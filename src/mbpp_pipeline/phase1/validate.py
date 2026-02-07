"""Validation utilities for MBPP entries."""

import ast

from loguru import logger

from mbpp_pipeline.phase1.schema import MBPPEntry


def validate_entry(entry: MBPPEntry) -> bool:
    """Check that an MBPP entry has valid, parseable Python code and tests.

    Returns True if the entry is valid.
    """
    if not entry.text.strip():
        logger.warning(f"Task {entry.task_id}: empty description")
        return False

    if not entry.code.strip():
        logger.warning(f"Task {entry.task_id}: empty code")
        return False

    try:
        ast.parse(entry.code)
    except SyntaxError as e:
        logger.warning(f"Task {entry.task_id}: code syntax error: {e}")
        return False

    if not entry.test_list:
        logger.warning(f"Task {entry.task_id}: no tests")
        return False

    for i, test in enumerate(entry.test_list):
        try:
            ast.parse(test)
        except SyntaxError as e:
            logger.warning(f"Task {entry.task_id}: test[{i}] syntax error: {e}")
            return False

    return True


def load_and_validate(entries: list[MBPPEntry]) -> list[MBPPEntry]:
    """Filter entries, keeping only those that pass validation."""
    valid = [e for e in entries if validate_entry(e)]
    logger.info(f"Validated {len(valid)}/{len(entries)} entries")
    return valid
