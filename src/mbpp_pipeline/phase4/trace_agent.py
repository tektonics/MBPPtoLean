"""TraceAgentSolution: Top-level orchestrator for Python→Lean autoformalization."""

from typing import List, Optional

import dspy
from loguru import logger
from pydantic import BaseModel

from mbpp_pipeline.config import Phase4Config
from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase3.schema import SolverResult
from mbpp_pipeline.phase4.baseline_agent import BaselineTranslationAgent, TraceAgentOutput
from mbpp_pipeline.phase4.bridge import build_benchmark_data, mbpp_to_signature
from mbpp_pipeline.phase4.self_debug import SelfDebugAgent
from mbpp_pipeline.phase4.self_improve import SelfImprovementAgent
from verina.benchmark.report import EvaluationTaskArtifact
from verina.benchmark.solution import (
    FewshotExample,
    GenCodeInput,
    GenCodeOutput,
    GenProofInput,
    GenProofOutput,
    GenSpecInput,
    GenSpecOutput,
    SimpleSolution,
)
from verina.dataset.schema import Signature


class TraceAgentConfig(BaseModel):
    """Configuration for the Trace Agent pipeline."""

    baseline_lm: dspy.LM
    judge_lm: Optional[dspy.LM] = None
    debug_lm: Optional[dspy.LM] = None
    improve_lm: Optional[dspy.LM] = None
    dspy_module_cls: type = dspy.Predict
    dspy_module_name: str = "Predict"
    max_debug_iterations: int = 10
    max_improve_iterations: int = 3
    min_score_threshold: int = 7

    class Config:
        arbitrary_types_allowed = True


class TraceAgentSolution(SimpleSolution):
    """Orchestrates the 3-agent pipeline: baseline → self-debug → self-improve.

    Inherits from Verina's SimpleSolution to satisfy the benchmark interface.
    """

    def __init__(self, config: TraceAgentConfig):
        super().__init__(SimpleSolution.Preference.NO_GENERATED_AS_REF)
        self.agent_config = config

        # Initialize sub-agents
        self.baseline_agent = BaselineTranslationAgent(
            lm=config.baseline_lm,
            dspy_module_cls=config.dspy_module_cls,
        )

        from mbpp_pipeline.config import DebugConfig, ImproveConfig

        debug_config = DebugConfig(max_iterations=config.max_debug_iterations)
        debug_lm = config.debug_lm or config.baseline_lm

        self.debug_agent = SelfDebugAgent(
            lm=debug_lm,
            config=debug_config,
            dspy_module=config.dspy_module_name,
        )

        if config.judge_lm is not None:
            improve_config = ImproveConfig(
                max_iterations=config.max_improve_iterations,
                min_score_threshold=config.min_score_threshold,
            )
            improve_lm = config.improve_lm or config.baseline_lm
            self.improve_agent: Optional[SelfImprovementAgent] = SelfImprovementAgent(
                judge_lm=config.judge_lm,
                improve_lm=improve_lm,
                debug_agent=self.debug_agent,
                config=improve_config,
                dspy_module_cls=config.dspy_module_cls,
            )
        else:
            self.improve_agent = None

    @staticmethod
    def name() -> str:
        return "trace_agent"

    async def run_full_pipeline(
        self,
        entry: MBPPEntry,
        solver_result: SolverResult,
    ) -> TraceAgentOutput:
        """Run the full 3-agent pipeline on a single MBPP entry.

        1. baseline_agent.translate() → initial Lean artifacts
        2. self_debug_agent.debug_loop() → compiling Lean artifacts
        3. self_improve_agent.improve_loop() → refined Lean artifacts
        """
        solution_code = solver_result.generated_solution or entry.code
        signature = mbpp_to_signature(entry, solution_code)

        # Step 1: Baseline translation
        logger.info(f"Task {entry.task_id}: starting baseline translation")
        output = await self.baseline_agent.translate(entry, solver_result, signature)

        # Step 2: Self-debug loop
        logger.info(f"Task {entry.task_id}: starting self-debug loop")
        output = await self.debug_agent.debug_loop(output, signature, entry.text)

        # Step 3: Self-improve loop (if judge is configured)
        if self.improve_agent is not None:
            logger.info(f"Task {entry.task_id}: starting self-improve loop")
            python_code = solver_result.generated_solution or entry.code
            output = await self.improve_agent.improve_loop(
                output, python_code, entry.text, signature
            )

        return output

    def output_to_artifact(self, output: TraceAgentOutput) -> EvaluationTaskArtifact:
        """Convert TraceAgentOutput to Verina's EvaluationTaskArtifact."""
        return EvaluationTaskArtifact(
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

    # --- SimpleSolution interface methods ---

    async def gen_code(
        self, data_id, input: GenCodeInput,
        fewshot_examples: List[FewshotExample[GenCodeInput, GenCodeOutput]],
        checkpoint=None,
    ) -> GenCodeOutput:
        """Generate code only (delegates to baseline agent's code generation)."""
        with dspy.context(lm=self.agent_config.baseline_lm):
            from mbpp_pipeline.phase4.signatures import Python2LeanCodeSig
            gen = self.agent_config.dspy_module_cls(Python2LeanCodeSig)
            from verina.baseline.generate import clean_output
            from verina.dataset.template import LeanGenerationTaskTemplate

            template = LeanGenerationTaskTemplate(input.signature)
            resp = await gen.acall(
                python_code="",
                description=input.description,
                lean_signature=template.render_code_signature(),
            )
            return GenCodeOutput(
                imports=clean_output(resp.imports, isImportsOrAux=True),
                code_aux=clean_output(resp.code_aux, isImportsOrAux=True),
                code=clean_output(resp.code, isImportsOrAux=False),
            )

    async def gen_spec(
        self, data_id, input: GenSpecInput,
        fewshot_examples: List[FewshotExample[GenSpecInput, GenSpecOutput]],
        checkpoint=None,
    ) -> GenSpecOutput:
        """Generate specification only."""
        with dspy.context(lm=self.agent_config.baseline_lm):
            from mbpp_pipeline.phase4.signatures import Python2LeanSpecSig
            from verina.baseline.generate import clean_output

            gen = self.agent_config.dspy_module_cls(Python2LeanSpecSig)
            resp = await gen.acall(
                python_code="",
                tests="",
                description=input.description,
            )
            return GenSpecOutput(
                imports=clean_output(resp.imports, isImportsOrAux=True),
                precond_aux=clean_output(resp.precond_aux, isImportsOrAux=True),
                precond=clean_output(resp.precond, isImportsOrAux=False),
                postcond_aux=clean_output(resp.postcond_aux, isImportsOrAux=True),
                postcond=clean_output(resp.postcond, isImportsOrAux=False),
            )

    async def gen_proof(
        self, data_id, input: GenProofInput,
        fewshot_examples: List[FewshotExample[GenProofInput, GenProofOutput]],
        checkpoint=None,
    ) -> GenProofOutput:
        """Generate proof only."""
        with dspy.context(lm=self.agent_config.baseline_lm):
            from mbpp_pipeline.phase4.signatures import Python2LeanProofSig
            from verina.baseline.generate import (
                clean_output,
                proof_task_template_from_input,
            )

            gen = self.agent_config.dspy_module_cls(Python2LeanProofSig)
            task_template = proof_task_template_from_input(input)
            resp = await gen.acall(
                task_template=task_template,
                description=input.description,
            )
            return GenProofOutput(
                imports=clean_output(resp.imports, isImportsOrAux=True),
                proof_aux=clean_output(resp.proof_aux, isImportsOrAux=True),
                proof=clean_output(resp.proof, isImportsOrAux=False),
            )


def create_trace_agent(config: Phase4Config) -> TraceAgentSolution:
    """Factory: create a TraceAgentSolution from Phase4Config."""
    baseline_lm = config.baseline_lm_config.get_model()

    judge_lm = None
    if config.judge_lm_config:
        judge_lm = config.judge_lm_config.get_model()

    dspy_module_cls = _resolve_dspy_module(config.dspy_module)

    agent_config = TraceAgentConfig(
        baseline_lm=baseline_lm,
        judge_lm=judge_lm,
        dspy_module_cls=dspy_module_cls,
        dspy_module_name=config.dspy_module,
        max_debug_iterations=config.debug_config.max_iterations,
        max_improve_iterations=config.improve_config.max_iterations,
        min_score_threshold=config.improve_config.min_score_threshold,
    )

    return TraceAgentSolution(agent_config)


def _resolve_dspy_module(name: str):
    """Resolve DSPy module class from config string."""
    modules = {
        "Predict": dspy.Predict,
        "ChainOfThought": dspy.ChainOfThought,
    }
    return modules.get(name, dspy.Predict)
