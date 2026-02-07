"""State verification tools for pipeline data integrity."""

import json
from pathlib import Path

from loguru import logger


class StateVerifier:  # A
    """Verifies data integrity and state consistency across pipeline phases."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def verify_jsonl_integrity(self, filepath: str) -> tuple[int, list[str]]:
        """Verify a JSONL file has valid JSON on every line.

        Returns:
            (valid_count, list_of_error_messages)
        """
        path = Path(filepath)
        if not path.exists():
            return 0, [f"File not found: {filepath}"]

        valid = 0
        errors = []
        with open(path) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    valid += 1
                except json.JSONDecodeError as e:
                    errors.append(f"Line {i}: {e}")
        return valid, errors

    def verify_phase_outputs_exist(self) -> list[str]:
        """Check that expected output files exist for completed phases."""
        issues = []
        expected = [
            ("Phase 1", self.data_dir / "mbpp_full.jsonl"),
            ("Phase 2", self.data_dir / "mbpp_mutated.jsonl"),
            ("Phase 3", self.data_dir / "solver_results.jsonl"),
            ("Phase 4", self.data_dir / "lean_artifacts"),
            ("Phase 5", self.data_dir / "verification_report.json"),
        ]
        for name, path in expected:
            if not path.exists():
                issues.append(f"{name}: output missing at {path}")
            else:
                logger.debug(f"{name}: output exists at {path}")
        return issues

    def verify_lean_artifacts_match_metadata(self) -> list[str]:
        """Check that every .lean file has a corresponding .json and vice versa."""
        issues = []
        artifacts_dir = self.data_dir / "lean_artifacts"
        if not artifacts_dir.exists():
            return ["Phase 4 artifacts directory does not exist"]

        lean_stems = {p.stem for p in artifacts_dir.glob("*.lean")}
        json_stems = {p.stem for p in artifacts_dir.glob("*.json")}

        for stem in lean_stems - json_stems:
            issues.append(f"{stem}.lean has no matching .json metadata")
        for stem in json_stems - lean_stems:
            issues.append(f"{stem}.json has no matching .lean file")

        return issues

    def run_all_checks(self) -> dict:
        """Run all state verification checks."""
        results = {}

        # Check phase outputs exist
        output_issues = self.verify_phase_outputs_exist()
        results["phase_outputs"] = {"issues": output_issues, "ok": len(output_issues) == 0}

        # Check JSONL integrity for each phase
        for name, filename in [
            ("phase1", "mbpp_full.jsonl"),
            ("phase2", "mbpp_mutated.jsonl"),
            ("phase3", "solver_results.jsonl"),
        ]:
            path = self.data_dir / filename
            if path.exists():
                count, errors = self.verify_jsonl_integrity(str(path))
                results[name] = {"valid_entries": count, "errors": errors, "ok": len(errors) == 0}

        # Check lean artifact consistency
        artifact_issues = self.verify_lean_artifacts_match_metadata()
        results["lean_artifacts"] = {"issues": artifact_issues, "ok": len(artifact_issues) == 0}

        all_ok = all(v.get("ok", False) for v in results.values())
        logger.info(f"State verification: {'PASS' if all_ok else 'FAIL'}")
        return results
