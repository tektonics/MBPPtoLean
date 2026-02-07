"""DSPy Signatures for Python→Lean 4 autoformalization."""

from dspy import InputField, OutputField
from dspy import Signature as DspySignature

# --- Signature 1: Python → Lean Code ---

PYTHON2LEAN_CODE_PROMPT = """
You are an expert in both Python and Lean 4.
Given Python code, a task description, and a Lean 4 function signature,
translate the Python code into equivalent Lean 4 code.
Rules:
- Use Lean 4 syntax only (NOT Lean 3).
- Do NOT use sorry, admit, or axiom.
- Do NOT import Std or Init.
- Use a[i]! instead of a[i] for array/list access when needed.
""".strip()


class Python2LeanCodeSig(DspySignature):
    python_code = InputField(desc="Python source code to translate")
    description = InputField(desc="Natural language description of the task")
    lean_signature = InputField(desc="Lean 4 function signature template")
    imports = OutputField(desc="Lean 4 imports needed. Keep empty if not needed.")
    code_aux = OutputField(desc="Auxiliary Lean 4 definitions. Keep empty if not needed.")
    code = OutputField(desc="Lean 4 function body implementing the task.")


Python2LeanCodeSig.__doc__ = PYTHON2LEAN_CODE_PROMPT


# --- Signature 2: Python → Lean Specification ---

PYTHON2LEAN_SPEC_PROMPT = """
You are an expert in Lean 4 formal verification.
Given Python code, its test cases, and a task description,
generate a Lean 4 precondition and postcondition that formally specify the function.
The precondition should be as permissive as possible.
The postcondition should be sound and complete w.r.t. the task description.
Rules:
- Use Lean 4 syntax only (NOT Lean 3).
- Add @[reducible, simp] to auxiliary definitions.
- Do NOT import Std or Init.
""".strip()


class Python2LeanSpecSig(DspySignature):
    python_code = InputField(desc="Python source code")
    tests = InputField(desc="Python test cases (assert statements)")
    description = InputField(desc="Natural language task description")
    imports = OutputField(desc="Lean 4 imports needed. Keep empty if not needed.")
    precond_aux = OutputField(
        desc="Auxiliary definitions for precondition. Keep empty if not needed."
    )
    precond = OutputField(desc="Lean 4 precondition body (Prop).")
    postcond_aux = OutputField(
        desc="Auxiliary definitions for postcondition. Keep empty if not needed."
    )
    postcond = OutputField(desc="Lean 4 postcondition body (Prop).")


Python2LeanSpecSig.__doc__ = PYTHON2LEAN_SPEC_PROMPT


# --- Signature 3: Generate Lean Proof ---

PYTHON2LEAN_PROOF_PROMPT = """
You are an expert in Lean 4 theorem proving.
Given a complete Lean 4 task template with code and specification,
generate a proof that the code satisfies the specification.
Rules:
- Use Lean 4 syntax only (NOT Lean 3).
- Do NOT use sorry, admit, or axiom.
- Unfold definitions and use simp/omega/decide as appropriate.
""".strip()


class Python2LeanProofSig(DspySignature):
    task_template = InputField(desc="Full Lean 4 code with placeholders for proof")
    description = InputField(desc="Natural language task description")
    imports = OutputField(desc="Lean 4 imports needed. Keep empty if not needed.")
    proof_aux = OutputField(desc="Auxiliary lemmas for the proof. Keep empty if not needed.")
    proof = OutputField(desc="Lean 4 proof that the code satisfies the specification.")


Python2LeanProofSig.__doc__ = PYTHON2LEAN_PROOF_PROMPT


# --- Signature 4: Proof Refinement (with error feedback) ---

PYTHON2LEAN_PROOF_REFINEMENT_PROMPT = """
You are an expert in Lean 4 theorem proving.
A previous proof attempt failed with the given error.
Fix the proof using the error message and previous attempt as reference.
Rules:
- Use Lean 4 syntax only (NOT Lean 3).
- Do NOT use sorry, admit, or axiom.
- You can ignore unused variable warnings.
""".strip()


class Python2LeanProofRefinementSig(DspySignature):
    task_template = InputField(desc="Full Lean 4 code with placeholders for proof")
    description = InputField(desc="Natural language task description")
    prev_imports = InputField(desc="Previously generated imports")
    prev_proof_aux = InputField(desc="Previously generated proof auxiliary")
    prev_proof = InputField(desc="Previously generated proof")
    prev_error = InputField(desc="Error message from previous attempt")
    imports = OutputField(desc="Lean 4 imports needed. Keep empty if not needed.")
    proof_aux = OutputField(desc="Auxiliary lemmas for the proof. Keep empty if not needed.")
    proof = OutputField(desc="Improved Lean 4 proof.")


Python2LeanProofRefinementSig.__doc__ = PYTHON2LEAN_PROOF_REFINEMENT_PROMPT


# --- Signature 5: LLM Judge for Lean quality ---

LEAN_JUDGE_PROMPT = """
You are a Lean 4 expert judge. Evaluate the quality of the generated Lean 4 code,
specification, and proof against the original Python task.
Score each dimension from 1-10 and provide actionable feedback.
""".strip()


class LeanJudgeSig(DspySignature):
    python_code = InputField(desc="Original Python code")
    lean_code = InputField(desc="Generated Lean 4 file content")
    description = InputField(desc="Natural language task description")
    correctness_score = OutputField(
        desc="Score 1-10: Does the Lean code match the Python semantics?"
    )
    completeness_score = OutputField(desc="Score 1-10: How complete is the specification?")
    proof_score = OutputField(desc="Score 1-10: How sound is the proof?")
    feedback = OutputField(desc="Specific, actionable feedback for improvement.")


LeanJudgeSig.__doc__ = LEAN_JUDGE_PROMPT


# --- Signature 6: Reflective Improvement ---

LEAN_REFLECT_PROMPT = """
You are an expert in Lean 4. Given the current Lean 4 code and judge feedback,
improve all components (code, specification, proof).
Focus on the weakest areas identified by the judge.
Rules:
- Use Lean 4 syntax only (NOT Lean 3).
- Do NOT use sorry, admit, or axiom.
""".strip()


class LeanReflectSig(DspySignature):
    lean_code = InputField(desc="Current Lean 4 file content")
    judge_feedback = InputField(desc="Judge's feedback and scores")
    description = InputField(desc="Natural language task description")
    imports = OutputField(desc="Improved Lean 4 imports.")
    code_aux = OutputField(desc="Improved code auxiliary definitions.")
    code = OutputField(desc="Improved Lean 4 code body.")
    precond_aux = OutputField(desc="Improved precondition auxiliary.")
    precond = OutputField(desc="Improved precondition.")
    postcond_aux = OutputField(desc="Improved postcondition auxiliary.")
    postcond = OutputField(desc="Improved postcondition.")
    proof_aux = OutputField(desc="Improved proof auxiliary.")
    proof = OutputField(desc="Improved proof.")


LeanReflectSig.__doc__ = LEAN_REFLECT_PROMPT
