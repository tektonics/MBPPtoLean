# Phase 2: Adversarial Mutation Specification

## Entry Point
`mbpp_pipeline.phase2.adversarial.build_adversarial_dataset(entries, operator_names, ...)`

## Input
- List of `MBPPEntry` from Phase 1

## Output
- `data/mbpp_mutated.jsonl` — one `MutatedEntry` per line

## Mutation Operators
All operators are tree-sitter-based (no LibCST dependency):

| Operator | Key | Description |
|----------|-----|-------------|
| RenameVariableOperator | rename_variable | Renames function parameters and their body references |
| RemoveTypeAnnotationOperator | remove_type_annotation | Strips type annotations from params and return types |
| RenameUserTypeOperator | rename_user_type | Renames class names and propagates references |
| RenameBuiltinTypeOperator | rename_builtin_type | Creates aliases for builtin types in annotations |

## Adversarial Filter
When `require_adversarial_filter=True`, mutated code must still pass the original test suite (semantic equivalence check via `safe_exec()`).
