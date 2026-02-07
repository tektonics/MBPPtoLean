# MBPP Lean Pipeline

Adversarial autoformalization pipeline that takes [MBPP](https://huggingface.co/datasets/google-research-datasets/mbpp) Python programming problems, generates adversarial mutations, solves them with LLMs, auto-formalizes solutions into Lean 4, and verifies the results via Verina.

## Prerequisites

- **Docker** and **Docker Compose**
- API keys for at least one LLM provider (OpenAI, Anthropic, Together, or Vertex AI)

## Quick Start

```bash
# Clone with submodules (verina is a git submodule)
git clone --recurse-submodules <repo-url>
cd mbpp_lean_pipeline

# Configure API keys
cp .env.example .env
# Edit .env and fill in your keys

# Build the Docker image (includes Lean 4 v4.18.0 + Verina)
docker compose build pipeline

# Run the full pipeline (use --limit to control API cost)
docker compose run --rm pipeline mbpp-pipeline run configs/pipeline.toml --limit 5
```

## Pipeline Phases

The pipeline has 5 sequential phases. You can run them individually or all at once with `run`.

| Command | Description | Output |
|---------|-------------|--------|
| `export` | Export MBPP dataset to JSONL | `data/mbpp_full.jsonl` |
| `mutate` | Generate adversarial mutations (rename variables, remove type annotations, etc.) | `data/mbpp_mutated.jsonl` |
| `solve` | Solve tasks with LLMs | `data/solver_results.jsonl` |
| `formalize` | Auto-formalize passing solutions to Lean 4 (baseline + self-debug + self-improve) | `data/lean_artifacts/*.lean` |
| `verify` | Verify Lean artifacts via compilation and evaluation | `data/verification_report.json` |
| `run` | Run all phases 1-5 sequentially | All of the above |

All commands except `verify` accept `--limit`/`-n` to cap the number of entries processed.

```bash
# Run individual phases
docker compose run --rm pipeline mbpp-pipeline export configs/pipeline.toml
docker compose run --rm pipeline mbpp-pipeline mutate configs/pipeline.toml
docker compose run --rm pipeline mbpp-pipeline solve configs/pipeline.toml --limit 10
docker compose run --rm pipeline mbpp-pipeline formalize configs/pipeline.toml --limit 5
docker compose run --rm pipeline mbpp-pipeline verify configs/pipeline.toml

# Debug shell inside container
docker compose run --rm pipeline bash
```

## Testing

```bash
# Run tests inside Docker
docker compose run --rm pipeline uv run pytest

# With coverage or verbose output
docker compose run --rm pipeline uv run pytest -v
```

Dev dependencies (pytest, hypothesis, ruff) are in the `[project.optional-dependencies] dev` group.

## Verina

This pipeline is built on top of [Verina](./verina), included as a git submodule. Verina provides:

- **Lean compilation** -- `lake lean` execution for checking generated `.lean` files
- **Proof refinement** -- iterative compile-refine loop used by the self-debug agent in Phase 4
- **DSPy signatures** -- code, spec, and proof generation signatures used by the baseline translation agent
- **Benchmark evaluation** -- metrics and reporting used by Phase 5 verification
- **Lean project environment** -- lakefile.lean and dependency management (including Mathlib)

All formalization (Phase 4) and verification (Phase 5) work flows through Verina.

## Tech Stack

- **[Verina](./verina)** -- Lean compilation, proof refinement, benchmark evaluation
- **Lean 4** v4.18.0 -- formalization target
- **DSPy** -- LLM programming framework
- **litellm** -- unified LLM API layer (OpenAI, Anthropic, Together, Vertex)
- **Prefect** -- workflow orchestration
- **tree-sitter** -- Python AST manipulation for mutations
- **Typer** -- CLI framework
- **Pydantic** -- schema validation

## License

See repository for license details.
