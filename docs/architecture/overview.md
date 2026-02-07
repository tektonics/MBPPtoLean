# System Architecture

## Overview

The MBPP-to-Lean pipeline is a 5-phase system that converts Python programming problems from the MBPP dataset into formally verified Lean 4 code. It runs entirely inside Docker with Lean 4 v4.18.0 + Mathlib.

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Docker Container                              │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                        │
│  │ Phase 1  │──>│ Phase 2  │   │ Phase 3  │                        │
│  │ Export   │   │ Mutate   │   │ Solve    │                        │
│  └──────────┘   └──────────┘   └────┬─────┘                        │
│       │                              │                               │
│       │              ┌───────────────┘                               │
│       ▼              ▼                                               │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐    │
│  │       Phase 4           │    │         Verina (submodule)   │    │
│  │    Formalize            │───>│  - ProofRefinementSolution   │    │
│  │  ┌───────────────────┐  │    │  - LeanGenerationTemplate   │    │
│  │  │ BaselineTranslator│  │    │  - BenchmarkMetrics          │    │
│  │  │ SelfDebugAgent    │  │    │  - lake lean <file>          │    │
│  │  │ SelfImproveAgent  │  │    └──────────────────────────────┘    │
│  │  └───────────────────┘  │                                        │
│  └────────────┬────────────┘                                        │
│               │                                                      │
│               ▼                                                      │
│  ┌──────────────────────────┐                                       │
│  │       Phase 5            │                                       │
│  │       Verify             │                                       │
│  └──────────────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow

Each phase reads from the previous phase's JSONL output:

| Phase | Input | Output | Format |
|-------|-------|--------|--------|
| 1 Export | HuggingFace MBPP dataset | `data/mbpp_full.jsonl` | MBPPEntry |
| 2 Mutate | `data/mbpp_full.jsonl` | `data/mbpp_mutated.jsonl` | MutatedEntry |
| 3 Solve | `data/mbpp_full.jsonl` | `data/solver_results.jsonl` | SolverResult |
| 4 Formalize | Phases 1+3 output | `data/lean_artifacts/*.lean` + `*.json` | TraceAgentOutput |
| 5 Verify | Phases 1+3+4 output | `data/verification_report.json` | PipelineReport |

## External Dependencies

- **Verina** (git submodule): Provides LLM config, Lean templates, proof refinement, compilation metrics
- **DSPy 3.1.2**: LLM prompting framework (Signatures, Predict, ChainOfThought)
- **litellm**: Multi-provider LLM routing (Anthropic, OpenAI, Together, Vertex)
- **tree-sitter**: Python AST parsing for code mutations
- **Lean 4 v4.18.0**: Theorem prover, invoked via `lake lean <file>`
- **Mathlib**: Lean 4 math library (pre-built oleans cached in Docker image)

## Design Decisions

1. **Verina as submodule, not fork**: Pipeline imports Verina as-is without modification. Changes to Verina are upstream concerns.
2. **Phase-based JSONL pipeline**: Each phase writes JSONL, enabling phase-by-phase reruns and debugging.
3. **Phase 4 filters to passing only**: Only entries that passed Python tests in Phase 3 are formalized, avoiding wasted API calls.
4. **Proof refinement delegated to Verina**: SelfDebugAgent wraps Verina's ProofRefinementSolution rather than reimplementing the compile-refine loop.
