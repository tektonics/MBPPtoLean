# Coding Standards

## Language
- Python 3.11+
- Type hints on all function signatures
- Pydantic BaseModel for all data schemas

## Style
- Ruff for linting and formatting (config in `config/linting/ruff.toml`)
- Line length: 100 characters
- Import sorting: isort-compatible (via ruff)

## Comments
- Python comment syntax for review markers: `# A`, `# HIGH-RISK-UNREVIEWED`, `# HIGH-RISK-REVIEWED`
- Docstrings on all public functions and classes

## Async
- Phases 3, 4, 5 use async/await
- `asyncio.Semaphore` for concurrency control
- Runner entry points use `asyncio.run()`

## Error Handling
- Use loguru for all logging
- Catch and log exceptions per-task in batch operations; do not let one failure abort the batch
- Never silently swallow exceptions

## Configuration
- All config via TOML files loaded into Pydantic models
- No hardcoded API keys, model names, or file paths
- Defaults in Pydantic models, overrides in TOML

## Dependencies
- Verina imported as a library, never modified
- Pin critical deps: dspy==3.1.2, prefect==3.4.1
- Use `verina @ file:///app/verina` in Docker context
