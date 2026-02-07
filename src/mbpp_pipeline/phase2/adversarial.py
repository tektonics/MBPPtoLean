"""Adversarial dataset generation: mutate + filter semantically equivalent variants."""

import json
from pathlib import Path
from random import Random
from typing import List

from loguru import logger

from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase2.mutations import OPERATOR_REGISTRY, MutationOperator
from mbpp_pipeline.phase2.schema import MutatedEntry
from mbpp_pipeline.utils.python_exec import safe_exec
from mbpp_pipeline.utils.treesitter import parse_python


def check_semantic_equivalence(
    entry: MBPPEntry,
    mutated_code: str,
    timeout: int = 10,
) -> bool:
    """Run original tests on mutated code to check semantic equivalence."""
    test_code = "\n".join(entry.test_list)
    if entry.test_setup_code:
        test_code = entry.test_setup_code + "\n" + test_code
    passed, _ = safe_exec(mutated_code, test_code, timeout=timeout)
    return passed


def build_adversarial_dataset(
    entries: List[MBPPEntry],
    operator_names: List[str],
    max_mutations_per_entry: int = 3,
    require_adversarial_filter: bool = False,
    seed: int = 42,
) -> List[MutatedEntry]:
    """Generate mutated variants for each MBPP entry.

    Args:
        entries: Validated MBPP entries.
        operator_names: Which mutation operators to apply.
        max_mutations_per_entry: Max mutations per entry.
        require_adversarial_filter: If True, only keep mutations that pass tests.
        seed: RNG seed for reproducibility.

    Returns:
        List of MutatedEntry objects.
    """
    rng = Random(seed)
    operators: List[MutationOperator] = []
    for name in operator_names:
        cls = OPERATOR_REGISTRY.get(name)
        if cls is None:
            logger.warning(f"Unknown operator '{name}', skipping")
            continue
        operators.append(cls())

    if not operators:
        logger.warning("No valid mutation operators; returning empty dataset")
        return []

    results: List[MutatedEntry] = []
    for entry in entries:
        tree = parse_python(entry.code)
        count = 0
        for op in operators:
            if count >= max_mutations_per_entry:
                break
            try:
                mutated_code, records = op.apply(entry.code, tree, rng)
            except Exception as e:
                logger.debug(f"Task {entry.task_id}, op {op.__class__.__name__}: {e}")
                continue

            if not records or mutated_code == entry.code:
                continue

            mutation_id = f"{entry.task_id}_{records[0].mutation_type.value}_{count}"

            tests_pass: bool | None = None
            if require_adversarial_filter:
                tests_pass = check_semantic_equivalence(entry, mutated_code)
                if not tests_pass:
                    logger.debug(
                        f"Task {entry.task_id} mutation {mutation_id} fails tests, skipping"
                    )
                    continue

            me = MutatedEntry.from_mbpp_entry(
                entry, mutated_code, mutation_id, records
            )
            me.tests_pass_on_mutated = tests_pass
            results.append(me)
            count += 1

    logger.info(f"Generated {len(results)} mutated entries from {len(entries)} originals")
    return results


def save_mutated_entries(entries: List[MutatedEntry], output_path: str | Path) -> None:
    """Write MutatedEntry list to JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")
    logger.info(f"Wrote {len(entries)} mutated entries to {output_path}")


def load_mutated_entries(path: str | Path) -> List[MutatedEntry]:
    """Load MutatedEntry list from JSONL."""
    entries: List[MutatedEntry] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(MutatedEntry.model_validate_json(line))
    return entries
