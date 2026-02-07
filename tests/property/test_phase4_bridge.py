"""Property-based tests for Phase 4 bridge module."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

import pytest

from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase3.schema import SolverResult
from mbpp_pipeline.phase4.bridge import build_benchmark_data, mbpp_to_signature

SAMPLE_ENTRIES = [
    MBPPEntry(
        task_id=1,
        text="Write a function to add two numbers.",
        code="def add(a, b):\n    return a + b",
        test_list=["assert add(1, 2) == 3"],
        test_setup_code="",
        challenge_test_list=[],
    ),
    MBPPEntry(
        task_id=2,
        text="Write a function to check if a number is even.",
        code="def is_even(n):\n    return n % 2 == 0",
        test_list=["assert is_even(4) == True"],
        test_setup_code="",
        challenge_test_list=[],
    ),
]


@pytest.mark.parametrize("entry", SAMPLE_ENTRIES)
def test_mbpp_to_signature_extracts_function_name(entry):  # A
    """Bridge correctly extracts function name from Python code."""
    sig = mbpp_to_signature(entry, entry.code)
    assert sig.name is not None
    assert len(sig.name) > 0


@pytest.mark.parametrize("entry", SAMPLE_ENTRIES)
def test_mbpp_to_signature_extracts_params(entry):  # A
    """Bridge extracts at least one parameter from functions with args."""
    sig = mbpp_to_signature(entry, entry.code)
    assert len(sig.parameters) > 0


@pytest.mark.parametrize("entry", SAMPLE_ENTRIES)
def test_build_benchmark_data_produces_valid_data(entry):  # A
    """build_benchmark_data creates a BenchmarkData with required fields."""
    sr = SolverResult(
        task_id=entry.task_id,
        mutation_id=None,
        model_name="test",
        prompt_style="chat",
        generated_solution=entry.code,
        passes_tests=True,
        is_from_adversarial=False,
        error=None,
    )
    data = build_benchmark_data(entry, sr)
    assert data.data_id is not None
    assert data.signature is not None
