# Phase 4 Agent Flow Diagram

```
                    ┌─────────────────┐
                    │   MBPPEntry +    │
                    │  SolverResult    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  bridge.py      │
                    │  mbpp_to_sig()  │
                    └────────┬────────┘
                             │
                    ┌────────▼─────────────────┐
                    │  BaselineTranslationAgent │
                    │  Python → Lean (one-shot) │
                    │  code + spec + proof      │
                    └────────┬─────────────────┘
                             │
                    ┌────────▼─────────────────┐
                    │     SelfDebugAgent        │
                    │  Verina ProofRefinement   │
                    │  compile → error → refine │
                    │  (up to N iterations)     │
                    └────────┬─────────────────┘
                             │
                    ┌────────▼─────────────────┐
                    │  SelfImprovementAgent     │
                    │  judge → reflect → retry  │
                    │  (up to M iterations)     │
                    └────────┬─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  .lean file +   │
                    │  .json metadata │
                    └─────────────────┘
```
