"""Integration tests for Phase 2 mutation pipeline."""
# IMMUTABLE: Do not modify these tests. Fix implementation if tests fail.

import ast

from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase2.adversarial import build_adversarial_dataset

SAMPLE_ENTRIES = [
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
        text="Square a number.",
        code="def square(x):\n    return x * x",
        test_list=["assert square(3) == 9"],
        test_setup_code="",
        challenge_test_list=[],
    ),
]


def test_build_adversarial_dataset_produces_output():  # A
    """Mutation pipeline produces at least one mutated entry per input."""
    mutated = build_adversarial_dataset(
        entries=SAMPLE_ENTRIES,
        operator_names=["rename_variable"],
        max_mutations_per_entry=1,
        require_adversarial_filter=False,
        seed=42,
    )
    assert len(mutated) >= len(SAMPLE_ENTRIES)


def test_mutated_code_is_valid_python():  # A
    """All mutated code must still be valid Python."""
    mutated = build_adversarial_dataset(
        entries=SAMPLE_ENTRIES,
        operator_names=["rename_variable", "remove_type_annotation"],
        max_mutations_per_entry=2,
        require_adversarial_filter=False,
        seed=42,
    )
    for entry in mutated:
        ast.parse(entry.mutated_code)


def test_mutation_records_are_populated():  # A
    """Mutated entries include at least one mutation record."""
    mutated = build_adversarial_dataset(
        entries=SAMPLE_ENTRIES,
        operator_names=["rename_variable"],
        max_mutations_per_entry=1,
        require_adversarial_filter=False,
        seed=42,
    )
    has_records = any(len(m.mutations_applied) > 0 for m in mutated)
    assert has_records
