"""Sub-agent 2: Proof generation via Verina's ProofRefinementSolution.

After the baseline agent translates Python→Lean (code + spec), we have Lean
artifacts. This module constructs a GenProofInput and delegates directly to
Verina's ProofRefinementSolution for the compile→refine loop.
"""

import dspy
from loguru import logger
from verina.baseline.config import BaselineConfig
from verina.baseline.proof_refinement import ProofRefinementSolution
from verina.benchmark.solution import (
    GenProofInput,
    GenProofOutput,
    merge_imports,
)
from verina.dataset.schema import Signature

from mbpp_pipeline.config import DebugConfig
from mbpp_pipeline.phase4.baseline_agent import TraceAgentOutput


class SelfDebugAgent:
    """Delegates proof generation to Verina's ProofRefinementSolution."""

    def __init__(
        self,
        lm: dspy.LM,
        config: DebugConfig,
        dspy_module: str = "Predict",
    ):
        self.lm = lm
        self.config = config

        # Build Verina's BaselineConfig for ProofRefinementSolution
        baseline_config = BaselineConfig(
            name="mbpp_proof_refinement",
            refinements=config.max_iterations,
            dspy_module=dspy_module,
        )
        self.proof_solution = ProofRefinementSolution(baseline_config)

    def _build_proof_input(
        self,
        output: TraceAgentOutput,
        signature: Signature,
        description: str,
    ) -> GenProofInput:
        """Construct Verina's GenProofInput from our TraceAgentOutput."""
        return GenProofInput(
            description=description,
            signature=signature,
            task_imports="",
            task_aux="",
            code_spec_imports=output.imports,
            code_aux=output.code_aux,
            code=output.code,
            precond_aux=output.precond_aux,
            precond=output.precond or "True -- no precondition",
            postcond_aux=output.postcond_aux,
            postcond=output.postcond,
        )

    async def debug_loop(
        self,
        output: TraceAgentOutput,
        signature: Signature,
        description: str,
    ) -> TraceAgentOutput:
        """Generate proof using Verina's ProofRefinementSolution.

        Constructs a GenProofInput from the translated Lean code+spec,
        then calls Verina's iterative compile→refine loop.
        """
        proof_input = self._build_proof_input(output, signature, description)

        with dspy.context(lm=self.lm):
            proof_output: GenProofOutput = await self.proof_solution.gen_proof(
                data_id="mbpp_debug",
                input=proof_input,
                fewshot_examples=[],
            )

        # Update output with proof results
        output.proof_aux = proof_output.proof_aux
        output.proof = proof_output.proof

        # Merge any new imports from proof generation
        if proof_output.imports.strip():
            output.imports = merge_imports([output.imports, proof_output.imports])

        # Read explicit status flags from extra_info  #A
        output.compile_success = proof_output.extra_info.get("compile_success", False)
        output.iterations = proof_output.extra_info.get("refined_times", 0)
        output.tactic_solved = proof_output.extra_info.get("tactic_solved", False)

        logger.info(
            f"Proof generation: iterations={output.iterations}, "
            f"compile_success={output.compile_success}, "
            f"tactic_solved={output.tactic_solved}"
        )

        return output
