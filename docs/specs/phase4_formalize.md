# Phase 4: Lean 4 Autoformalization Specification

## Entry Point
`mbpp_pipeline.runner.run_phase4(cfg, limit=None)`

## Input
- `MBPPEntry` from Phase 1
- `SolverResult` from Phase 3 (only entries with `passes_tests=True`)

## Output
- `data/lean_artifacts/mbpp_<task_id>.lean` — Lean 4 source file
- `data/lean_artifacts/mbpp_<task_id>.json` — TraceAgentOutput metadata

## Sub-Agent Pipeline

### Agent 1: BaselineTranslationAgent (baseline_agent.py)
- One-shot translation via three DSPy signatures:
  - `Python2LeanCodeSig` → imports, code_aux, code
  - `Python2LeanSpecSig` → precond, postcond (+ aux variants)
  - `Python2LeanProofSig` → proof, proof_aux
- Uses `LeanGenerationTaskTemplate` to render Lean file structure

### Agent 2: SelfDebugAgent (self_debug.py)
- Wraps Verina's `ProofRefinementSolution`
- Iterative loop: generate proof → compile → read errors → refine
- Configurable max iterations (default: 10)
- Only refines the proof; code and spec from Agent 1 are preserved

### Agent 3: SelfImprovementAgent (self_improve.py)
- Judge LM scores the Lean output (separate LM config)
- If score < threshold, reflect on failures and re-run debug agent
- Configurable max iterations (default: 3) and min score threshold (default: 7)

### Orchestration: TraceAgentSolution (trace_agent.py)
- Inherits from Verina's `SimpleSolution`
- Chains: baseline → debug → improve
- `run_full_pipeline()` is the main entry point

## Bridge (bridge.py)
- `mbpp_to_signature()`: Extracts Lean-compatible `Signature` from Python code via AST
- `build_benchmark_data()`: Creates Verina `BenchmarkData` from MBPP entry + solver result
