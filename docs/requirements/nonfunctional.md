# Non-Functional Requirements

## NFR-1: Containerization
- All phases must run inside a single Docker image
- Lean 4 + Mathlib + Python 3.11 available in the image
- API keys passed via environment variables, never baked into image

## NFR-2: Cost Control
- `--limit` flag on all LLM-calling phases to restrict API usage
- Phase 4 filters to only passing entries to avoid wasted API calls

## NFR-3: Reproducibility
- Phase 2 mutations are seeded for deterministic output
- All pipeline outputs written to `data/` as JSONL for auditability

## NFR-4: Resumability
- Each phase reads from the previous phase's output files
- Phases can be re-run independently without re-running earlier phases

## NFR-5: Portability
- Repository is self-contained with Verina as a git submodule
- `git clone --recurse-submodules` provides everything needed
- No external dependencies beyond Docker and API keys
