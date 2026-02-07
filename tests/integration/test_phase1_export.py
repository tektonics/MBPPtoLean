"""Integration tests for Phase 1 MBPP export."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

import ast

import pytest

from mbpp_pipeline.phase1.export_mbpp import load_mbpp_jsonl
from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase1.validate import load_and_validate, validate_entry


@pytest.fixture
def sample_jsonl(tmp_path):  # A
    """Create a sample JSONL file with known entries."""
    entries = [
        MBPPEntry(
            task_id=1,
            text="Add two numbers.",
            code="def add(a, b):\n    return a + b",
            test_list=["assert add(1, 2) == 3"],
            test_setup_code="",
            challenge_test_list=[],
        ),
        MBPPEntry(
            task_id=2,
            text="Check even.",
            code="def is_even(n):\n    return n % 2 == 0",
            test_list=["assert is_even(4) == True"],
            test_setup_code="",
            challenge_test_list=[],
        ),
    ]
    path = tmp_path / "test.jsonl"
    with open(path, "w") as f:
        for e in entries:
            f.write(e.model_dump_json() + "\n")
    return path, entries


def test_load_mbpp_jsonl_roundtrip(sample_jsonl):  # A
    """Entries written to JSONL can be loaded back."""
    path, original = sample_jsonl
    loaded = load_mbpp_jsonl(str(path))
    assert len(loaded) == len(original)
    for orig, load in zip(original, loaded, strict=True):
        assert orig.task_id == load.task_id
        assert orig.code == load.code


def test_validate_entry_accepts_valid_python(sample_jsonl):  # A
    """validate_entry accepts entries with parseable Python code."""
    _, entries = sample_jsonl
    for entry in entries:
        assert validate_entry(entry) is True


def test_validate_entry_rejects_invalid_python():  # A
    """validate_entry rejects entries with unparseable code."""
    entry = MBPPEntry(
        task_id=99,
        text="Bad code.",
        code="def broken(:\n    pass",
        test_list=[],
        test_setup_code="",
        challenge_test_list=[],
    )
    assert validate_entry(entry) is False


def test_load_and_validate_filters_invalid(sample_jsonl):  # A
    """load_and_validate only returns entries that parse."""
    _, entries = sample_jsonl
    valid = load_and_validate(entries)
    assert len(valid) == len(entries)
    for e in valid:
        ast.parse(e.code)
