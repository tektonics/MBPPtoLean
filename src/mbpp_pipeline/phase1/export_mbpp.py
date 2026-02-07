"""Export MBPP dataset from HuggingFace cache to JSONL."""

from pathlib import Path

from datasets import load_dataset
from loguru import logger

from mbpp_pipeline.phase1.schema import MBPPEntry


def export_mbpp_to_jsonl(
    cache_dir: str | Path,
    output_path: str | Path,
) -> list[MBPPEntry]:
    """Load MBPP from HuggingFace datasets and write to JSONL.

    Args:
        cache_dir: Directory with cached HF dataset (or download location).
        output_path: Path to write the JSONL output.

    Returns:
        List of validated MBPPEntry objects.
    """
    cache_dir = Path(cache_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading MBPP dataset from cache_dir={cache_dir}")
    ds = load_dataset("mbpp", "full", cache_dir=str(cache_dir), trust_remote_code=True)

    entries: list[MBPPEntry] = []
    for split_name in ds:
        for row in ds[split_name]:
            entry = MBPPEntry(
                task_id=row["task_id"],
                text=row["text"],
                code=row["code"],
                test_list=row["test_list"],
                test_setup_code=row.get("test_setup_code", ""),
                challenge_test_list=row.get("challenge_test_list", []),
            )
            entries.append(entry)

    # Deduplicate by task_id
    seen: set[int] = set()
    unique: list[MBPPEntry] = []
    for e in entries:
        if e.task_id not in seen:
            seen.add(e.task_id)
            unique.append(e)
    entries = unique

    with open(output_path, "w") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")

    logger.info(f"Exported {len(entries)} MBPP entries to {output_path}")
    return entries


def load_mbpp_jsonl(path: str | Path) -> list[MBPPEntry]:
    """Load MBPP entries from a JSONL file."""
    entries: list[MBPPEntry] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(MBPPEntry.model_validate_json(line))
    return entries
