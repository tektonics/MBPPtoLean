# Phase 3: LLM Task Solving Specification

## Entry Point
`mbpp_pipeline.phase3.solver.TaskSolver.solve_batch(entries)`

## Input
- List of `MBPPEntry` from Phase 1

## Output
- `data/solver_results.jsonl` — one `SolverResult` per line

## Schema: SolverResult
```python
class SolverResult(BaseModel):
    task_id: int
    mutation_id: Optional[str]
    model_name: str
    prompt_style: str
    generated_solution: Optional[str]
    passes_tests: bool
    is_from_adversarial: bool
    error: Optional[str]
```

## LLM Integration
- Uses DSPy `SolveMBPPSig` signature
- LLM configured via `LMConfig` (provider + model_name)
- Prompt styles: "chat" (default), "fim"
- Concurrency controlled by `asyncio.Semaphore(max_concurrent)`

## Test Execution
- Generated solutions are executed against MBPP test cases via `safe_exec()`
- `passes_tests` is set based on execution result
