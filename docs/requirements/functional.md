# Functional Requirements

## FR-1: MBPP Dataset Export
- Export the full MBPP dataset from HuggingFace to local JSONL
- Each entry must contain: task_id, text (description), code (reference solution), test_list, test_setup_code, challenge_test_list
- All entries must parse as valid Python via `ast.parse()`
- Support `--limit` flag to restrict number of entries

## FR-2: Adversarial Mutation
- Apply tree-sitter-based mutations to Python code
- Supported mutation types: rename_variable, remove_type_annotation, rename_user_type, rename_builtin_type
- Configurable max mutations per entry
- Optional adversarial filter: mutated code must still pass original tests (semantic equivalence)
- Deterministic via configurable random seed

## FR-3: LLM Task Solving
- Solve MBPP tasks using configurable LLM (via DSPy + litellm)
- Support chat and FIM prompt styles
- Execute generated solutions against test cases
- Record pass/fail status per entry
- Configurable concurrency via semaphore
- Support `--limit` flag

## FR-4: Lean 4 Autoformalization
- Translate passing Python solutions into Lean 4 code + specifications + proofs
- Three-agent pipeline: baseline translation, self-debug (proof refinement), self-improvement (judge loop)
- Baseline agent: one-shot Python-to-Lean via DSPy signatures
- Self-debug agent: iterative proof refinement using Verina's ProofRefinementSolution with Lean compiler feedback
- Self-improvement agent: judge scores output, reflect on failures, re-attempt
- Output: `.lean` file + `.json` metadata per entry
- Support `--limit` flag
- Only formalize entries that passed Phase 3 tests

## FR-5: Verification
- Verify Lean artifacts using Verina's evaluation metrics
- Check: code compilation, spec compilation, unit tests, proof validity
- Produce summary report with pass rates
- Output: JSON verification report

## FR-6: Pipeline Orchestration
- `run` command executes all phases sequentially
- Individual phase commands for selective execution
- TOML-based configuration for all parameters
- `--limit` flag applies per-phase
