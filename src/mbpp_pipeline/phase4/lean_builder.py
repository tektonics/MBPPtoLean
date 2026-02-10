"""Assemble final .lean file from TraceAgentOutput using Verina templates."""

from verina.dataset.schema import Signature, TestCase
from verina.dataset.template import LeanGenerationTaskTemplate
from verina.lean import sanitize_lean_imports


def build_lean_file(
    signature: Signature,
    imports: str,
    code_aux: str,
    code: str,
    precond_aux: str,
    precond: str,
    postcond_aux: str,
    postcond: str,
    proof_aux: str,
    proof: str,
    task_imports: str = "",
    task_aux: str = "",
) -> str:
    """Render a complete .lean file using the Verina template engine.

    This produces a file with benchmark markers that Verina's metrics can parse.
    """
    template = LeanGenerationTaskTemplate(signature)
    content = ""

    # Task imports
    if task_imports.strip():
        content += template.render_imports(task_imports, "task") + "\n"

    # Solution imports
    if imports.strip():
        content += template.render_imports(
            sanitize_lean_imports(imports), "llm_solution"
        ) + "\n"

    # Task aux
    if task_aux.strip():
        content += template.render_aux(task_aux, "task") + "\n"

    # Precondition
    if precond_aux.strip():
        content += template.render_aux(precond_aux, "precond") + "\n"
    if not precond.strip():
        precond = "True -- no precondition"
    content += template.render_precond(precond) + "\n"

    # Code
    if code_aux.strip():
        content += template.render_aux(code_aux, "code") + "\n"
    content += template.render_code(code) + "\n"

    # Postcondition
    if postcond_aux.strip():
        content += template.render_aux(postcond_aux, "postcond") + "\n"
    content += template.render_postcond(postcond) + "\n"

    # Proof
    if proof_aux.strip():
        content += template.render_aux(proof_aux, "proof") + "\n"
    content += template.render_proof(proof) + "\n"

    return content


def build_lean_file_for_verification(
    signature: Signature,
    imports: str,
    code_aux: str,
    code: str,
    precond_aux: str,
    precond: str,
    postcond_aux: str,
    postcond: str,
    proof_aux: str,
    proof: str,
    tests: list[TestCase],
    task_imports: str = "",
    task_aux: str = "",
) -> str:
    """Build a .lean file with #guard unit tests appended for verification."""
    base = build_lean_file(
        signature=signature,
        imports=imports,
        code_aux=code_aux,
        code=code,
        precond_aux=precond_aux,
        precond=precond,
        postcond_aux=postcond_aux,
        postcond=postcond,
        proof_aux=proof_aux,
        proof=proof,
        task_imports=task_imports,
        task_aux=task_aux,
    )

    template = LeanGenerationTaskTemplate(signature)
    for idx, tc in enumerate(tests):
        base += "\n" + template.render_code_unit_test(tc, test_idx=idx)

    return base
