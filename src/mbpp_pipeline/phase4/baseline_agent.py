"""Sub-agent 1: Initial Python→Lean translation."""

import dspy
from loguru import logger
from pydantic import BaseModel, Field
from verina.baseline.generate import clean_output, create_placeholder
from verina.dataset.schema import Signature
from verina.dataset.template import LeanGenerationTaskTemplate

from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase3.schema import SolverResult
from mbpp_pipeline.phase4.lean_builder import build_lean_file
from mbpp_pipeline.phase4.signatures import (
    Python2LeanCodeSig,
    Python2LeanProofSig,
    Python2LeanSpecSig,
)


class TraceAgentOutput(BaseModel):
    """Output from the TraceAgent pipeline (all Lean components)."""

    imports: str = ""
    code_aux: str = ""
    code: str = ""
    precond_aux: str = ""
    precond: str = ""
    postcond_aux: str = ""
    postcond: str = ""
    proof_aux: str = ""
    proof: str = ""
    compile_success: bool | None = None
    judge_scores: dict = Field(default_factory=dict)
    iterations: int = 0


class BaselineTranslationAgent:
    """Generate initial Lean 4 translation from Python."""

    def __init__(self, lm: dspy.LM, dspy_module_cls=None):
        self.lm = lm
        self.dspy_module_cls = dspy_module_cls or dspy.Predict

    async def translate(
        self,
        entry: MBPPEntry,
        solver_result: SolverResult,
        signature: Signature,
    ) -> TraceAgentOutput:
        """Produce initial Lean 4 code, spec, and proof from Python."""
        python_code = solver_result.generated_solution or entry.code
        template = LeanGenerationTaskTemplate(signature)

        output = TraceAgentOutput()

        with dspy.context(lm=self.lm):
            # 1. Generate Lean code
            try:
                lean_sig_str = template.render_code_signature()
                code_gen = self.dspy_module_cls(Python2LeanCodeSig)
                code_resp = await code_gen.acall(
                    python_code=python_code,
                    description=entry.text,
                    lean_signature=lean_sig_str,
                )
                output.imports = clean_output(code_resp.imports, isImportsOrAux=True)
                output.code_aux = clean_output(code_resp.code_aux, isImportsOrAux=True)
                output.code = clean_output(code_resp.code, isImportsOrAux=False)
            except Exception as e:
                logger.error(f"Task {entry.task_id}: code generation failed: {e}")

            # 2. Generate Lean specification
            try:
                tests_str = "\n".join(entry.test_list)
                spec_gen = self.dspy_module_cls(Python2LeanSpecSig)
                spec_resp = await spec_gen.acall(
                    python_code=python_code,
                    tests=tests_str,
                    description=entry.text,
                )
                output.precond_aux = clean_output(spec_resp.precond_aux, isImportsOrAux=True)
                output.precond = clean_output(spec_resp.precond, isImportsOrAux=False)
                output.postcond_aux = clean_output(spec_resp.postcond_aux, isImportsOrAux=True)
                output.postcond = clean_output(spec_resp.postcond, isImportsOrAux=False)
                # Merge imports
                spec_imports = clean_output(spec_resp.imports, isImportsOrAux=True)
                if spec_imports.strip():
                    if output.imports.strip():
                        output.imports = output.imports + "\n" + spec_imports
                    else:
                        output.imports = spec_imports
            except Exception as e:
                logger.error(f"Task {entry.task_id}: spec generation failed: {e}")

            # 3. Generate Lean proof
            try:
                # Build the task template with code+spec filled in
                task_template_str = build_lean_file(
                    signature=signature,
                    imports=output.imports,
                    code_aux=output.code_aux,
                    code=output.code,
                    precond_aux=output.precond_aux,
                    precond=output.precond or "True",
                    postcond_aux=output.postcond_aux,
                    postcond=output.postcond,
                    proof_aux=create_placeholder("proof_aux"),
                    proof=create_placeholder("proof"),
                )
                proof_gen = self.dspy_module_cls(Python2LeanProofSig)
                proof_resp = await proof_gen.acall(
                    task_template=f"```lean4\n{task_template_str}```",
                    description=entry.text,
                )
                output.proof_aux = clean_output(proof_resp.proof_aux, isImportsOrAux=True)
                output.proof = clean_output(proof_resp.proof, isImportsOrAux=False)
                # Merge proof imports
                proof_imports = clean_output(proof_resp.imports, isImportsOrAux=True)
                if proof_imports.strip():
                    if output.imports.strip():
                        output.imports = output.imports + "\n" + proof_imports
                    else:
                        output.imports = proof_imports
            except Exception as e:
                logger.error(f"Task {entry.task_id}: proof generation failed: {e}")

        return output
