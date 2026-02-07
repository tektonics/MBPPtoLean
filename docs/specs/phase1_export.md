# Phase 1: MBPP Export Specification

## Entry Point
`mbpp_pipeline.phase1.export_mbpp.export_mbpp_to_jsonl(cache_dir, output_file)`

## Input
- HuggingFace `mbpp` dataset (downloaded and cached)

## Output
- `data/mbpp_full.jsonl` — one `MBPPEntry` per line

## Schema: MBPPEntry
```python
class MBPPEntry(BaseModel):
    task_id: int
    text: str              # Problem description
    code: str              # Reference Python solution
    test_list: List[str]   # Test assertions
    test_setup_code: str   # Setup code for tests
    challenge_test_list: List[str]  # Additional challenge tests
```

## Validation
- `validate_entry()`: verifies `ast.parse(entry.code)` succeeds
- `load_and_validate()`: filters to entries that parse successfully
