"""Property-based tests for Phase 2 mutation operators."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

import ast
from random import Random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mbpp_pipeline.phase2.mutations import (
    OPERATOR_REGISTRY,
    RemoveTypeAnnotationOperator,
    RenameVariableOperator,
)
from mbpp_pipeline.utils.treesitter import parse_python

SIMPLE_FUNCTIONS = [
    "def add(a, b):\n    return a + b",
    "def greet(name):\n    return 'hello ' + name",
    "def square(x):\n    return x * x",
    "def identity(val):\n    return val",
]


@given(seed=st.integers(min_value=0, max_value=10000))
@settings(max_examples=20)
@pytest.mark.parametrize("source", SIMPLE_FUNCTIONS)
def test_rename_variable_preserves_parseable_python(source, seed):  # A
    """Renamed variables still produce valid Python."""
    tree = parse_python(source)
    op = RenameVariableOperator()
    mutated, _records = op.apply(source, tree, Random(seed))
    # Mutated code must still parse
    ast.parse(mutated)


@given(seed=st.integers(min_value=0, max_value=10000))
@settings(max_examples=20)
@pytest.mark.parametrize("source", SIMPLE_FUNCTIONS)
def test_remove_type_annotation_preserves_parseable_python(source, seed):  # A
    """Removing type annotations still produces valid Python."""
    typed_source = source.replace("def add(a, b)", "def add(a: int, b: int) -> int")
    tree = parse_python(typed_source)
    op = RemoveTypeAnnotationOperator()
    mutated, _records = op.apply(typed_source, tree, Random(seed))
    ast.parse(mutated)


def test_all_operators_registered():  # A
    """All expected operators exist in the registry."""
    expected = {
        "rename_variable",
        "remove_type_annotation",
        "rename_user_type",
        "rename_builtin_type",
    }
    assert set(OPERATOR_REGISTRY.keys()) == expected
