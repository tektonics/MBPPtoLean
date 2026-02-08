"""Bridge: Convert MBPP data to Verina BenchmarkData format."""

import ast
import re
from typing import Any

from verina.dataset.parsing import BenchmarkLeanData
from verina.dataset.schema import (
    BenchmarkData,
    Parameter,
    RejectInput,
    Signature,
    SpecDesc,
    TestCase,
)

from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase3.schema import SolverResult

# Python type -> Lean type mapping
_PY_TO_LEAN_TYPE = {
    "int": "Int",
    "float": "Float",
    "str": "String",
    "bool": "Bool",
    "None": "Unit",
    "list": "List",
    "dict": "HashMap",
    "set": "HashSet",
    "tuple": "Prod",
    "List": "List",
    "Dict": "HashMap",
    "Set": "HashSet",
    "Tuple": "Prod",
    "Optional": "Option",
}


def _python_type_to_lean(py_type: str) -> str:
    """Convert a Python type annotation string to a Lean 4 type string."""
    py_type = py_type.strip()

    # Handle None/NoneType
    if py_type in ("None", "NoneType"):
        return "Unit"

    # Handle Optional[X] -> Option X
    m = re.match(r"Optional\[(.+)\]", py_type)
    if m:
        inner = _python_type_to_lean(m.group(1))
        return f"Option {inner}"

    # Handle List[X] -> List X
    m = re.match(r"(?:List|list)\[(.+)\]", py_type)
    if m:
        inner = _python_type_to_lean(m.group(1))
        return f"List {inner}"

    # Handle Dict[K, V] -> HashMap K V
    m = re.match(r"(?:Dict|dict)\[(.+),\s*(.+)\]", py_type)
    if m:
        k = _python_type_to_lean(m.group(1))
        v = _python_type_to_lean(m.group(2))
        return f"HashMap {k} {v}"

    # Handle Tuple[X, Y] -> Prod X Y (simplified)
    m = re.match(r"(?:Tuple|tuple)\[(.+)\]", py_type)
    if m:
        inner_parts = [_python_type_to_lean(p.strip()) for p in m.group(1).split(",")]
        if len(inner_parts) == 2:
            cross = "\u00d7"
            return f"({inner_parts[0]} {cross} {inner_parts[1]})"
        cross = "\u00d7"
        return f"({f' {cross} '.join(inner_parts)})"

    # Handle Set[X] -> HashSet X
    m = re.match(r"(?:Set|set)\[(.+)\]", py_type)
    if m:
        inner = _python_type_to_lean(m.group(1))
        return f"HashSet {inner}"

    # Simple type lookup
    if py_type in _PY_TO_LEAN_TYPE:
        return _PY_TO_LEAN_TYPE[py_type]
    # Pass through capitalized names as custom types (e.g. "Pair" → "Pair")
    if py_type and py_type[0].isupper():
        return py_type
    return "Int"


def _infer_node_type(node: ast.expr) -> str | None:  # //A
    """Infer a Python type string from an AST expression node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "bool"
        if isinstance(node.value, int):
            return "int"
        if isinstance(node.value, float):
            return "float"
        if isinstance(node.value, str):
            return "str"
        return None

    if isinstance(node, ast.List):
        if not node.elts:
            return "list"
        inner = _infer_node_type(node.elts[0])
        return f"List[{inner}]" if inner else "list"

    if isinstance(node, ast.Tuple):
        inner_types = [_infer_node_type(e) for e in node.elts]
        if all(inner_types):
            return f"Tuple[{', '.join(t for t in inner_types if t)}]"
        return "tuple"

    if isinstance(node, ast.Set):
        if not node.elts:
            return "set"
        inner = _infer_node_type(node.elts[0])
        return f"Set[{inner}]" if inner else "set"

    if isinstance(node, ast.Dict):
        if not node.keys or node.keys[0] is None:
            return "dict"
        k = _infer_node_type(node.keys[0])
        v = _infer_node_type(node.values[0]) if node.values else None
        if k and v:
            return f"Dict[{k}, {v}]"
        return "dict"

    if isinstance(node, ast.Call):
        # e.g. Pair(5, 24) → "Pair"
        if isinstance(node.func, ast.Name):
            return node.func.id
        return None

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        # Negative number literal like -1010
        inner = _infer_node_type(node.operand)
        return inner

    return None


def _infer_types_from_tests(  # //A
    func_name: str, test_list: list[str]
) -> list[str | None]:
    """Infer parameter types from test assertions.

    Returns a list of inferred Python type strings, one per positional arg.
    None means inference failed for that position.
    """
    inferred: list[str | None] = []

    for test_str in test_list:
        try:
            tree = ast.parse(test_str.strip())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            test_node = node.test
            # Handle assert func(...) == expected
            call_node = None
            if isinstance(test_node, ast.Compare) and isinstance(test_node.left, ast.Call):
                call_node = test_node.left
            elif isinstance(test_node, ast.Call):
                call_node = test_node
            if call_node is None:
                continue

            # Check function name matches
            if isinstance(call_node.func, ast.Name) and call_node.func.id == func_name:
                pass
            elif isinstance(call_node.func, ast.Attribute) and call_node.func.attr == func_name:
                pass
            else:
                continue

            # Infer type for each positional argument
            for i, arg in enumerate(call_node.args):
                arg_type = _infer_node_type(arg)
                # Extend inferred list if needed
                while len(inferred) <= i:
                    inferred.append(None)
                # Keep first successful inference per position
                if inferred[i] is None and arg_type is not None:
                    inferred[i] = arg_type

        # Stop after first successful parse with results
        if any(t is not None for t in inferred):
            break

    return inferred


def _extract_func_signature(
    code: str, test_list: list[str] | None = None
) -> tuple[str, list[tuple[str, str]], str] | None:
    """Extract function name, parameters, and return type from Python code.

    Returns:
        (func_name, [(param_name, param_type), ...], return_type) or None.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name

            # Infer types from tests if available
            test_inferred: list[str | None] = []
            if test_list:
                test_inferred = _infer_types_from_tests(func_name, test_list)

            params: list[tuple[str, str]] = []
            param_idx = 0
            for arg in node.args.args:
                param_name = arg.arg
                if param_name == "self":
                    continue
                if arg.annotation:
                    param_type = ast.unparse(arg.annotation)
                elif param_idx < len(test_inferred) and test_inferred[param_idx] is not None:
                    param_type = test_inferred[param_idx]
                else:
                    param_type = "int"
                params.append((param_name, param_type))
                param_idx += 1

            ret_type = ast.unparse(node.returns) if node.returns else "int"

            return func_name, params, ret_type

    return None


def mbpp_to_signature(entry: MBPPEntry, solution_code: str) -> Signature:
    """Parse Python AST to build a Verina Signature.

    Uses the solution code (or original code) to extract function info.
    Falls back to entry.code if solution has no function definitions.
    """
    result = _extract_func_signature(solution_code, entry.test_list)
    if result is None:
        result = _extract_func_signature(entry.code, entry.test_list)
    if result is None:
        # Last resort: make a generic signature
        return Signature(
            name="solution",
            parameters=[Parameter(param_name="x", param_type="Int")],
            return_type="Int",
        )

    func_name, params, ret_type = result
    lean_params = [
        Parameter(
            param_name=pname,
            param_type=_python_type_to_lean(ptype),
        )
        for pname, ptype in params
    ]
    lean_ret = _python_type_to_lean(ret_type)
    return Signature(name=func_name, parameters=lean_params, return_type=lean_ret)


def _parse_assert_value(expr_str: str) -> Any:
    """Try to evaluate a simple Python expression to get a test value."""
    try:
        return ast.literal_eval(expr_str)
    except (ValueError, SyntaxError):
        return expr_str


def mbpp_tests_to_verina_tests(
    entry: MBPPEntry,
    signature: Signature,
) -> tuple[list[TestCase], list[RejectInput]]:
    """Parse MBPP assert statements to extract TestCase and RejectInput objects."""
    test_cases: list[TestCase] = []

    for test_str in entry.test_list:
        try:
            tree = ast.parse(test_str.strip())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                test_node = node.test
                # Handle assert func(args) == expected
                if (
                    isinstance(test_node, ast.Compare)
                    and len(test_node.ops) == 1
                    and isinstance(test_node.ops[0], ast.Eq)
                ):
                    call_node = test_node.left
                    expected_node = test_node.comparators[0]

                    if isinstance(call_node, ast.Call):
                        # Extract args
                        input_dict: dict[str, Any] = {}
                        for i, arg in enumerate(call_node.args):
                            if i < len(signature.parameters):
                                pname = signature.parameters[i].param_name
                            else:
                                pname = f"arg{i}"
                            input_dict[pname] = _parse_assert_value(ast.unparse(arg))

                        expected = _parse_assert_value(ast.unparse(expected_node))
                        test_cases.append(
                            TestCase(
                                input=input_dict,
                                expected=expected,
                                unexpected=[],
                            )
                        )

    return test_cases, []


def build_benchmark_data(
    entry: MBPPEntry,
    solver_result: SolverResult,
) -> BenchmarkData:
    """Construct a Verina BenchmarkData skeleton from an MBPP entry + solver result.

    The lean_data fields are initially empty — Phase 4 agents populate them.
    """
    solution_code = solver_result.generated_solution or entry.code
    signature = mbpp_to_signature(entry, solution_code)
    test_cases, reject_inputs = mbpp_tests_to_verina_tests(entry, signature)

    lean_data = BenchmarkLeanData(
        task_imports="",
        solution_imports="",
        task_aux="",
        solution_aux="",
        code_aux="",
        precond_aux="",
        postcond_aux="",
        proof_aux="",
        code="",
        precond="True -- default precond",
        postcond="",
        proof="sorry",
    )

    return BenchmarkData(
        data_id=f"mbpp_{entry.task_id}",
        description=entry.text,
        signature=signature,
        lean_data=lean_data,
        spec_desc=SpecDesc(
            precond_desc="The input satisfies standard constraints for the task.",
            postcond_desc=f"The output satisfies: {entry.text}",
        ),
        reject_inputs=reject_inputs,
        tests=test_cases,
    )
