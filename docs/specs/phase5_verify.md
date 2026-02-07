# Phase 5: Verification Specification

## Entry Point
`mbpp_pipeline.phase5.verifier.PipelineVerifier.verify_full(data, output)`

## Input
- `BenchmarkData` (from bridge.py)
- `TraceAgentOutput` (from Phase 4 JSON metadata)

## Output
- `data/verification_report.json` — PipelineReport with per-task results and summary

## Verification Checks
Delegates to Verina's metric functions:

| Check | Verina Function | What It Verifies |
|-------|----------------|------------------|
| Code compilation | `metric_generated_code()` | Lean code compiles |
| Spec compilation | `metric_generated_spec_compile()` | Precond/postcond compile |
| Unit tests | `metric_generated_spec_unit_test_entry()` | Spec passes unit tests |
| Proof validity | `metric_generated_proof()` | Proof compiles without sorry |

## Report Summary
- Total entries verified
- Code/spec/proof pass rates
- Per-task detailed results
