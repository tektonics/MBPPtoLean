"""Property-based tests for Phase 3 schemas."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

from hypothesis import given, settings
from hypothesis import strategies as st

from mbpp_pipeline.phase3.schema import SolverResult


@given(
    task_id=st.integers(min_value=1, max_value=10000),
    passes=st.booleans(),
    solution=st.text(min_size=0, max_size=500),
)
@settings(max_examples=50)
def test_solver_result_roundtrip(task_id, passes, solution):  # A
    """SolverResult serializes and deserializes without data loss."""
    sr = SolverResult(
        task_id=task_id,
        mutation_id=None,
        model_name="test-model",
        prompt_style="chat",
        generated_solution=solution if solution else None,
        passes_tests=passes,
        is_from_adversarial=False,
        error=None,
    )
    json_str = sr.model_dump_json()
    restored = SolverResult.model_validate_json(json_str)
    assert restored.task_id == sr.task_id
    assert restored.passes_tests == sr.passes_tests
    assert restored.generated_solution == sr.generated_solution
