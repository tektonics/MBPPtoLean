# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

Everything runs in Docker. The image includes Lean 4 v4.18.0 + Mathlib and Python 3.11.

```bash
# Build
docker compose build pipeline

# Run full pipeline (use --limit/-n to control API cost)
docker compose run --rm pipeline mbpp-pipeline run configs/pipeline.toml --limit 5

# Run individual phases
docker compose run --rm pipeline mbpp-pipeline export configs/pipeline.toml
docker compose run --rm pipeline mbpp-pipeline mutate configs/pipeline.toml
docker compose run --rm pipeline mbpp-pipeline solve configs/pipeline.toml --limit 10
docker compose run --rm pipeline mbpp-pipeline formalize configs/pipeline.toml --limit 5
docker compose run --rm pipeline mbpp-pipeline verify configs/pipeline.toml

# Debug shell inside container
docker compose run --rm pipeline bash
```

API keys go in `.env` (copy from `.env.example`). The `--limit`/`-n` flag is available on export, mutate, solve, formalize, and run commands.

## Architecture

This is a 5-phase pipeline that takes MBPP Python problems, creates adversarial mutations, solves them via LLMs, auto-formalizes solutions into Lean 4, and verifies the results.

### Phase flow and data dependencies

```
Phase 1 (export)  → data/mbpp_full.jsonl
Phase 2 (mutate)  → data/mbpp_mutated.jsonl     (reads phase 1 output)
Phase 3 (solve)   → data/solver_results.jsonl    (reads phase 1 output)
Phase 4 (formalize) → data/lean_artifacts/*.lean + *.json  (reads phases 1+3)
Phase 5 (verify)  → data/verification_report.json (reads phases 1+3+4)
```

Phase 4 only formalizes entries that passed tests in Phase 3.

### Key schemas connecting phases

- `MBPPEntry` (phase1/schema.py) — raw MBPP problem with task_id, text, code, test_list
- `MutatedEntry` (phase2/schema.py) — entry + mutation records
- `SolverResult` (phase3/schema.py) — LLM-generated solution + passes_tests flag
- `TraceAgentOutput` (phase4/baseline_agent.py) — all Lean components (imports, code, precond, postcond, proof, etc.)
- `VerificationResult` (phase5/verifier.py) — per-task verification scores

### Verina dependency

Verina is a git submodule at `./verina`. The pipeline imports heavily from it:

- `verina.utils.lm.LMConfig` — LLM configuration (DSPy → litellm → provider APIs)
- `verina.baseline.proof_refinement.ProofRefinementSolution` — iterative compile-refine loop for proof generation (used by phase4/self_debug.py)
- `verina.baseline.generate.*` — DSPy signatures for code/spec/proof generation, `clean_output()`
- `verina.dataset.schema.*` — `BenchmarkData`, `Signature`, `Parameter`, `TestCase`
- `verina.dataset.template.LeanGenerationTaskTemplate` — renders `.lean` files with benchmark markers
- `verina.benchmark.metrics.*` — Lean compilation checking via `lake lean <file>`
- `verina.benchmark.report.EvaluationTaskArtifact` — evaluation model

Lean compilation happens via `lake lean <file>` with `LEAN_WORKING_DIR` pointing to the verina submodule (which has lakefile.lean + Mathlib deps).

### Phase 4 internals (formalization)

Phase 4 is the most complex. It chains three sub-agents:

1. **BaselineTranslationAgent** (baseline_agent.py) — one-shot Python→Lean translation via DSPy (code, spec, proof)
2. **SelfDebugAgent** (self_debug.py) — delegates to Verina's `ProofRefinementSolution` for iterative proof refinement with compiler feedback
3. **SelfImprovementAgent** (self_improve.py) — judge→reflect→debug loop using a separate judge LM

These are orchestrated by `TraceAgentSolution` in trace_agent.py.

### Config

All configuration is in `configs/pipeline.toml`, loaded into `PipelineConfig` (config.py). LLM models are configured per-phase via `LMConfig` sections (provider + model_name). The config flows through DSPy → litellm → provider APIs (OpenAI, Anthropic, Together, Vertex).

---

## Code Quality and Development Standards

### Core Principles

You are generating code for a human developer who maintains ultimate responsibility for code quality and decisions. Your role is to implement specifications precisely, not to make architectural decisions independently.

### Documentation Requirements

All code you generate must align with project documentation located in:
- `/docs/architecture/` - System architecture and design decisions
- `/docs/requirements/` - Functional and non-functional requirements
- `/docs/standards/` - Coding standards, best practices, design patterns
- `/docs/specs/` - Component specifications and interfaces
- `/docs/diagrams/` - Flowcharts, UML diagrams, sequence diagrams

**Before generating code**: Review relevant documentation. If specifications are ambiguous or incomplete, request clarification rather than making assumptions.

### Code Review Status Markers

Mark all functions you create or modify with review status comments:

- `//A` - AI-generated, not reviewed by human
- `//HIGH-RISK-UNREVIEWED` - Security-critical function requiring human review
- `//HIGH-RISK-REVIEWED` - Security-critical function approved by human

**Critical**: If you modify ANY line in a `//HIGH-RISK-REVIEWED` function, you MUST change its status to `//HIGH-RISK-UNREVIEWED`.

High-risk functions include:
- Authentication and authorization logic
- Data validation and sanitization
- Cryptographic operations
- Database access and queries
- File system operations
- Network request handling
- Payment processing
- User data handling

### Testing Requirements

#### Property-Based Tests (Read-Only)

Files in `/tests/property/` and `/tests/integration/` are IMMUTABLE. You may not:
- Modify existing tests to make code pass
- Delete or comment out failing tests
- Add mocks or stubs that circumvent test logic
- Hard-code values to satisfy test expectations

If tests fail, fix the implementation, not the tests.

#### Test Quality Standards

- Use property-based testing frameworks to verify behavior across input ranges
- Include state verification tests that check database/filesystem state directly
- For distributed systems, verify data consistency across nodes
- Tests must verify actual behavior, not implementation details
- No mocks/stubs unless explicitly specified in test requirements

#### Debug System Integration

Use the project's logging and monitoring system at `/debug/` which provides:
- Aggregated logs from distributed components
- Abstracted status reports (e.g., "Data synchronized to 3/4 nodes")
- State verification tools

Log meaningful information at appropriate levels. Do not rely solely on print statements or manual verification.

### Code Quality Standards

#### Linting and Formatting

- All code must pass linters defined in `/config/linting/`
- Use formatters defined in `/config/formatting/`
- Run linting before submitting code: `npm run lint` or `poetry run lint`

#### Complexity Management

- Minimize code complexity to preserve context window
- Prefer simple, explicit logic over clever, compact code
- Each line costs context window space - eliminate unnecessary code
- Extract complex logic into well-documented helper functions

### Task Breakdown Protocol

When given complex tasks:

1. **Request decomposition** if task spans multiple components
2. **Generate one component at a time** for human review
3. **Confirm specifications** before implementing each component
4. **Validate against requirements** before marking complete

Do not generate entire systems at once. Build incrementally with validation checkpoints.

### Pseudocode and Algorithms

When `/docs/pseudocode/` contains algorithm specifications:
- Implement exactly as specified
- Preserve logic flow and edge cases
- Document deviations with rationale

### Security Protocol

For any code touching:
- User authentication/authorization
- Sensitive data (PII, credentials, tokens)
- External APIs or databases
- File system or network operations

You MUST:
1. Mark with `//HIGH-RISK-UNREVIEWED`
2. Implement input validation and sanitization
3. Use parameterized queries (no string concatenation)
4. Follow principle of least privilege
5. Log security-relevant events

### Communication Standards

When uncertain:
- Request clarification on requirements
- Propose solutions with tradeoffs
- Explain complex implementation decisions
- Document assumptions in code comments

Do not:
- Make architectural decisions without approval
- Implement features not in specifications
- Bypass security measures for convenience
- Silently change test behavior to pass tests

### Prohibited Shortcuts

Never:
- Delete or modify tests to make code pass
- Use hard-coded values to satisfy tests (unless specified in requirements)
- Implement mock/stub logic that hides broken functionality
- Simplify complex requirements without approval
- Skip input validation on "internal" functions

### Success Criteria

Code is complete when:
- All specified tests pass without modification
- Linting passes without warnings
- Documentation is updated
- Review status markers are accurate
- Debug logging provides meaningful information
- Security considerations are addressed

---

## Docker build notes

- The Dockerfile is a multi-stage build: lean-base → python-base → runtime
- Verina's lake project files are copied first for Mathlib cache layer caching
- `pyproject.toml` uses `verina @ file:///app/verina` with `allow-direct-references = true` (hatchling requirement)
- A dummy `README.md` is touched in the verina copy because verina's pyproject.toml references it
