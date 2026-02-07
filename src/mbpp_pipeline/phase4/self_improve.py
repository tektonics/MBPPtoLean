"""Sub-agent 3: LLM Judge + reflective improvement loop."""

import dspy
from loguru import logger
from verina.baseline.generate import clean_output
from verina.dataset.schema import Signature

from mbpp_pipeline.config import ImproveConfig
from mbpp_pipeline.phase4.baseline_agent import TraceAgentOutput
from mbpp_pipeline.phase4.lean_builder import build_lean_file
from mbpp_pipeline.phase4.self_debug import SelfDebugAgent
from mbpp_pipeline.phase4.signatures import LeanJudgeSig, LeanReflectSig


class SelfImprovementAgent:
    """Judge-guided reflective improvement loop."""

    def __init__(
        self,
        judge_lm: dspy.LM,
        improve_lm: dspy.LM,
        debug_agent: SelfDebugAgent,
        config: ImproveConfig,
        dspy_module_cls=None,
    ):
        self.judge_lm = judge_lm
        self.improve_lm = improve_lm
        self.debug_agent = debug_agent
        self.config = config
        self.dspy_module_cls = dspy_module_cls or dspy.Predict

    async def improve_loop(
        self,
        output: TraceAgentOutput,
        python_code: str,
        description: str,
        signature: Signature,
    ) -> TraceAgentOutput:
        """Run judge→reflect→debug loop for quality improvement."""
        for iteration in range(self.config.max_iterations):
            # Build current Lean file for judging
            lean_content = build_lean_file(
                signature=signature,
                imports=output.imports,
                code_aux=output.code_aux,
                code=output.code,
                precond_aux=output.precond_aux,
                precond=output.precond or "True",
                postcond_aux=output.postcond_aux,
                postcond=output.postcond,
                proof_aux=output.proof_aux,
                proof=output.proof,
            )

            # Judge the current output
            try:
                with dspy.context(lm=self.judge_lm):
                    judge = self.dspy_module_cls(LeanJudgeSig)
                    judge_resp = await judge.acall(
                        python_code=python_code,
                        lean_code=lean_content,
                        description=description,
                    )

                correctness = _parse_score(judge_resp.correctness_score)
                completeness = _parse_score(judge_resp.completeness_score)
                proof_score = _parse_score(judge_resp.proof_score)
                feedback = judge_resp.feedback

                output.judge_scores = {
                    "correctness": correctness,
                    "completeness": completeness,
                    "proof": proof_score,
                    "feedback": feedback,
                }

                logger.info(
                    f"Improve iteration {iteration}: "
                    f"correctness={correctness}, completeness={completeness}, proof={proof_score}"
                )

                # Check if all scores meet threshold
                threshold = self.config.min_score_threshold
                if (
                    correctness >= threshold
                    and completeness >= threshold
                    and proof_score >= threshold
                ):
                    logger.info(f"All scores >= {threshold}, stopping improvement")
                    return output

            except Exception as e:
                logger.error(f"Improve iteration {iteration}: judge failed: {e}")
                return output

            # Reflect and improve
            try:
                with dspy.context(lm=self.improve_lm):
                    reflector = self.dspy_module_cls(LeanReflectSig)
                    reflect_resp = await reflector.acall(
                        lean_code=lean_content,
                        judge_feedback=feedback,
                        description=description,
                    )

                output.imports = (
                    clean_output(reflect_resp.imports, isImportsOrAux=True) or output.imports
                )
                output.code_aux = clean_output(reflect_resp.code_aux, isImportsOrAux=True)
                output.code = clean_output(reflect_resp.code, isImportsOrAux=False) or output.code
                output.precond_aux = clean_output(reflect_resp.precond_aux, isImportsOrAux=True)
                output.precond = (
                    clean_output(reflect_resp.precond, isImportsOrAux=False) or output.precond
                )
                output.postcond_aux = clean_output(reflect_resp.postcond_aux, isImportsOrAux=True)
                output.postcond = (
                    clean_output(reflect_resp.postcond, isImportsOrAux=False) or output.postcond
                )
                output.proof_aux = clean_output(reflect_resp.proof_aux, isImportsOrAux=True)
                output.proof = (
                    clean_output(reflect_resp.proof, isImportsOrAux=False) or output.proof
                )

            except Exception as e:
                logger.error(f"Improve iteration {iteration}: reflection failed: {e}")
                return output

            # Re-run debug loop to verify compilation after improvement
            output = await self.debug_agent.debug_loop(output, signature, description)

        return output


def _parse_score(value: str) -> int:
    """Parse a score value that might be a string like '7' or '7/10'."""
    try:
        s = str(value).strip()
        if "/" in s:
            s = s.split("/")[0].strip()
        return int(float(s))
    except (ValueError, TypeError):
        return 5  # default mid-range score
