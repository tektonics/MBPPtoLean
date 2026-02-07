"""Property-based tests for Phase 1 schemas."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

from hypothesis import given, settings
from hypothesis import strategies as st

from mbpp_pipeline.phase1.schema import MBPPEntry


@given(
    task_id=st.integers(min_value=1, max_value=10000),
    text=st.text(min_size=1, max_size=200),
    code=st.just("def f(x):\n    return x + 1"),
    test_list=st.lists(st.just("assert f(1) == 2"), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_mbpp_entry_roundtrip(task_id, text, code, test_list):  # A
    """MBPPEntry serializes and deserializes without data loss."""
    entry = MBPPEntry(
        task_id=task_id,
        text=text,
        code=code,
        test_list=test_list,
        test_setup_code="",
        challenge_test_list=[],
    )
    json_str = entry.model_dump_json()
    restored = MBPPEntry.model_validate_json(json_str)
    assert restored.task_id == entry.task_id
    assert restored.text == entry.text
    assert restored.code == entry.code
    assert restored.test_list == entry.test_list


@given(
    task_id=st.integers(min_value=1, max_value=10000),
    text=st.text(min_size=1, max_size=200),
)
@settings(max_examples=50)
def test_mbpp_entry_requires_valid_fields(task_id, text):  # A
    """MBPPEntry accepts valid inputs without error."""
    entry = MBPPEntry(
        task_id=task_id,
        text=text,
        code="pass",
        test_list=["assert True"],
        test_setup_code="",
        challenge_test_list=[],
    )
    assert entry.task_id == task_id
