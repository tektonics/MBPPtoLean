"""Phase 5: Verification via Verina pipeline."""

from typing import Optional

from loguru import logger
from pydantic import BaseModel

from mbpp_pipeline.phase4.baseline_agent import TraceAgentOutput
from mbpp_pipeline.phase4.lean_builder import build_lean_file
from verina.benchmark.common import BenchmarkSpecEvaluationConfig
from verina.benchmark.metrics import (
    CodeMetricScore,
    ProofMetricScore,
    SpecMetricScore,
    metric_generated_code,
    metric_generated_proof,
    metric_generated_spec_compile,
    metric_generated_spec_unit_test_entry,
)
from verina.benchmark.report import EvaluationTaskArtifact
from verina.dataset.schema import BenchmarkData, Signature
from verina.dataset.template import LeanGenerationTaskTemplate


class VerificationResult(BaseModel):
    """Aggregated verification result for a single entry."""

    task_id: str
    code_score: Optional[CodeMetricScore] = None
    precond_score: Optional[SpecMetricScore] = None
    postcond_score: Optional[SpecMetricScore] = None
    proof_score: Optional[ProofMetricScore] = None


class PipelineVerifier:
    """Delegates verification to Verina's metric functions."""

    def __init__(self, eval_spec_config: Optional[BenchmarkSpecEvaluationConfig] = None):
        self.eval_spec_config = eval_spec_config or BenchmarkSpecEvaluationConfig()

    async def verify_code(
        self,
        data: BenchmarkData,
        artifact: EvaluationTaskArtifact,
    ) -> CodeMetricScore:
        """Verify generated code: compilation + unit tests."""
        template = LeanGenerationTaskTemplate(data.signature)
        return await metric_generated_code(template, data, artifact)

    async def verify_spec(
        self,
        data: BenchmarkData,
        artifact: EvaluationTaskArtifact,
        evaluate_type: str = "postcond",
    ) -> SpecMetricScore:
        """Verify generated specification: compilation + unit tests."""
        template = LeanGenerationTaskTemplate(data.signature)

        # First check compilation
        score = await metric_generated_spec_compile(
            None, template, data, artifact, evaluate_type
        )

        # Then run unit tests if compilation succeeded
        if score.can_compile and self.eval_spec_config.unit_test:
            score = await metric_generated_spec_unit_test_entry(
                score, self.eval_spec_config, template, data, artifact, evaluate_type
            )

        return score

    async def verify_proof(
        self,
        data: BenchmarkData,
        artifact: EvaluationTaskArtifact,
    ) -> ProofMetricScore:
        """Verify generated proof: checks for cheat codes + compilation."""
        template = LeanGenerationTaskTemplate(data.signature)
        return await metric_generated_proof(template, data, artifact)

    async def verify_full(
        self,
        data: BenchmarkData,
        output: TraceAgentOutput,
    ) -> VerificationResult:
        """Run all verification checks on a complete TraceAgentOutput."""
        artifact = EvaluationTaskArtifact(
            imports=output.imports,
            code_aux=output.code_aux,
            code=output.code,
            precond_aux=output.precond_aux,
            precond=output.precond,
            postcond_aux=output.postcond_aux,
            postcond=output.postcond,
            proof_aux=output.proof_aux,
            proof=output.proof,
        )

        result = VerificationResult(task_id=data.data_id)

        try:
            result.code_score = await self.verify_code(data, artifact)
        except Exception as e:
            logger.error(f"{data.data_id}: code verification failed: {e}")

        try:
            result.precond_score = await self.verify_spec(data, artifact, "precond")
        except Exception as e:
            logger.error(f"{data.data_id}: precond verification failed: {e}")

        try:
            result.postcond_score = await self.verify_spec(data, artifact, "postcond")
        except Exception as e:
            logger.error(f"{data.data_id}: postcond verification failed: {e}")

        try:
            result.proof_score = await self.verify_proof(data, artifact)
        except Exception as e:
            logger.error(f"{data.data_id}: proof verification failed: {e}")

        return result
