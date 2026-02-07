# Phase 4 Formalization Pseudocode

## run_phase4(config, limit)

```
load entries from phase1 output
load solver_results from phase3 output
filter to solver_results where passes_tests == True
if limit: take first N

for each solver_result (concurrently, bounded by semaphore):
    entry = lookup MBPP entry by task_id
    signature = mbpp_to_signature(entry, solver_result.generated_solution)

    # Agent 1: Baseline translation
    output = baseline_agent.translate(entry, solver_result, signature)
        # calls Python2LeanCodeSig → imports, code_aux, code
        # calls Python2LeanSpecSig → precond, postcond
        # calls Python2LeanProofSig → proof

    # Agent 2: Self-debug (proof refinement)
    output = self_debug.debug_loop(output, signature, entry.text)
        # builds GenProofInput from output
        # delegates to Verina ProofRefinementSolution.gen_proof()
        # loop: generate proof → compile → if error, refine → repeat

    # Agent 3: Self-improvement
    output = self_improve.improve_loop(output, signature, entry.text)
        # judge LM scores the output (1-10)
        # if score < threshold:
        #     reflect on failures
        #     re-run self_debug
        # repeat up to max_iterations

    # Write outputs
    write .lean file from output fields
    write .json metadata from output.model_dump_json()
```

## mbpp_to_signature(entry, python_code)

```
parse python_code with ast.parse()
find first FunctionDef node
extract:
    function name
    parameter names and types (from annotations or default to Any)
    return type (from annotation or default to Any)
map Python types to Lean types:
    int → Int, float → Float, str → String, bool → Bool
    list → List, dict → HashMap, etc.
build Verina Signature(name, params, return_type)
```
