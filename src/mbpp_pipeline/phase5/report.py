"""Pipeline report aggregation."""

import json
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field
from verina.benchmark.metrics import LeanTestScore

from mbpp_pipeline.phase5.verifier import VerificationResult


class PipelineSummary(BaseModel):
    """Aggregate statistics across all verified entries."""

    total_entries: int = 0
    code_compile_count: int = 0
    code_test_pass_count: int = 0
    spec_compile_count: int = 0
    spec_sound_count: int = 0
    spec_complete_count: int = 0
    proof_compile_count: int = 0
    overall_verified_count: int = 0

    @property
    def code_compile_rate(self) -> float:
        return self.code_compile_count / max(self.total_entries, 1)

    @property
    def code_test_pass_rate(self) -> float:
        return self.code_test_pass_count / max(self.total_entries, 1)

    @property
    def spec_compile_rate(self) -> float:
        return self.spec_compile_count / max(self.total_entries, 1)

    @property
    def spec_sound_rate(self) -> float:
        return self.spec_sound_count / max(self.total_entries, 1)

    @property
    def spec_complete_rate(self) -> float:
        return self.spec_complete_count / max(self.total_entries, 1)

    @property
    def proof_compile_rate(self) -> float:
        return self.proof_compile_count / max(self.total_entries, 1)

    @property
    def overall_verification_rate(self) -> float:
        return self.overall_verified_count / max(self.total_entries, 1)

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "code_compile_rate": round(self.code_compile_rate, 4),
            "code_test_pass_rate": round(self.code_test_pass_rate, 4),
            "spec_compile_rate": round(self.spec_compile_rate, 4),
            "spec_sound_rate": round(self.spec_sound_rate, 4),
            "spec_complete_rate": round(self.spec_complete_rate, 4),
            "proof_compile_rate": round(self.proof_compile_rate, 4),
            "overall_verification_rate": round(self.overall_verification_rate, 4),
        }


class PipelineReport(BaseModel):
    """Full pipeline report with per-entry results and aggregate summary."""

    results: list[VerificationResult] = Field(default_factory=list)
    summary: PipelineSummary | None = None
    adversarial_summary: PipelineSummary | None = None
    original_summary: PipelineSummary | None = None

    def compute_summary(
        self,
        adversarial_ids: set | None = None,
    ) -> None:
        """Compute aggregate statistics from individual results."""
        all_results = self.results
        self.summary = _compute_summary_for(all_results)

        if adversarial_ids:
            adv = [r for r in all_results if r.task_id in adversarial_ids]
            orig = [r for r in all_results if r.task_id not in adversarial_ids]
            self.adversarial_summary = _compute_summary_for(adv)
            self.original_summary = _compute_summary_for(orig)

    def save(self, output_path: str | Path) -> None:
        """Save report as JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        if self.summary:
            data["summary_rates"] = self.summary.to_dict()
        if self.adversarial_summary:
            data["adversarial_summary_rates"] = self.adversarial_summary.to_dict()
        if self.original_summary:
            data["original_summary_rates"] = self.original_summary.to_dict()
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved verification report to {output_path}")


def _compute_summary_for(results: list[VerificationResult]) -> PipelineSummary:
    """Compute PipelineSummary from a list of VerificationResults."""
    summary = PipelineSummary(total_entries=len(results))

    for r in results:
        code_compiles = r.code_score is not None and r.code_score.can_compile
        code_tests_pass = r.code_score is not None and r.code_score.score == LeanTestScore.PASS
        spec_compiles = (r.precond_score is not None and r.precond_score.can_compile) or (
            r.postcond_score is not None and r.postcond_score.can_compile
        )
        spec_sound = (
            r.postcond_score is not None
            and r.postcond_score.sound_test_score.score == LeanTestScore.PASS
        )
        spec_complete = (
            r.postcond_score is not None
            and r.postcond_score.complete_test_score.score == LeanTestScore.PASS
        )
        proof_compiles = r.proof_score is not None and r.proof_score.can_compile

        if code_compiles:
            summary.code_compile_count += 1
        if code_tests_pass:
            summary.code_test_pass_count += 1
        if spec_compiles:
            summary.spec_compile_count += 1
        if spec_sound:
            summary.spec_sound_count += 1
        if spec_complete:
            summary.spec_complete_count += 1
        if proof_compiles:
            summary.proof_compile_count += 1
        if code_compiles and spec_compiles and proof_compiles:
            summary.overall_verified_count += 1

    return summary
