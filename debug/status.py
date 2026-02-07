"""Pipeline status reporting — abstracted status for each phase."""

import json
from pathlib import Path

from loguru import logger


class PipelineStatus:  # A
    """Provides abstracted status reports for the pipeline."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def phase1_status(self) -> dict:
        """Report Phase 1 (export) status."""
        path = self.data_dir / "mbpp_full.jsonl"
        if not path.exists():
            return {"phase": 1, "status": "not_started", "entries": 0}
        with open(path) as f:
            count = sum(1 for _ in f)
        return {"phase": 1, "status": "complete", "entries": count}

    def phase2_status(self) -> dict:
        """Report Phase 2 (mutate) status."""
        path = self.data_dir / "mbpp_mutated.jsonl"
        if not path.exists():
            return {"phase": 2, "status": "not_started", "entries": 0}
        with open(path) as f:
            count = sum(1 for _ in f)
        return {"phase": 2, "status": "complete", "entries": count}

    def phase3_status(self) -> dict:
        """Report Phase 3 (solve) status."""
        path = self.data_dir / "solver_results.jsonl"
        if not path.exists():
            return {"phase": 3, "status": "not_started", "total": 0, "passing": 0}
        total = 0
        passing = 0
        with open(path) as f:
            for line in f:
                total += 1
                data = json.loads(line)
                if data.get("passes_tests"):
                    passing += 1
        return {"phase": 3, "status": "complete", "total": total, "passing": passing}

    def phase4_status(self) -> dict:
        """Report Phase 4 (formalize) status."""
        artifacts_dir = self.data_dir / "lean_artifacts"
        if not artifacts_dir.exists():
            return {"phase": 4, "status": "not_started", "artifacts": 0, "compiling": 0}
        lean_files = list(artifacts_dir.glob("*.lean"))
        json_files = list(artifacts_dir.glob("*.json"))
        compiling = 0
        for jf in json_files:
            data = json.loads(jf.read_text())
            if data.get("compile_success"):
                compiling += 1
        return {
            "phase": 4,
            "status": "complete" if lean_files else "not_started",
            "artifacts": len(lean_files),
            "compiling": compiling,
        }

    def phase5_status(self) -> dict:
        """Report Phase 5 (verify) status."""
        path = self.data_dir / "verification_report.json"
        if not path.exists():
            return {"phase": 5, "status": "not_started"}
        data = json.loads(path.read_text())
        return {"phase": 5, "status": "complete", "summary": data.get("summary", {})}

    def full_status(self) -> list:
        """Report status for all phases."""
        statuses = [
            self.phase1_status(),
            self.phase2_status(),
            self.phase3_status(),
            self.phase4_status(),
            self.phase5_status(),
        ]
        for s in statuses:
            logger.info(f"Phase {s['phase']}: {s['status']}", **s)
        return statuses
