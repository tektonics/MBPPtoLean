"""Pipeline orchestrator: runs phases 1-5."""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from mbpp_pipeline.config import PipelineConfig
from mbpp_pipeline.phase1.export_mbpp import export_mbpp_to_jsonl, load_mbpp_jsonl
from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase1.validate import load_and_validate
from mbpp_pipeline.phase2.adversarial import (
    build_adversarial_dataset,
    load_mutated_entries,
    save_mutated_entries,
)
from mbpp_pipeline.phase2.schema import MutatedEntry
from mbpp_pipeline.phase3.schema import SolverResult
from mbpp_pipeline.phase3.solver import (
    TaskSolver,
    load_solver_results,
    save_solver_results,
)
from mbpp_pipeline.phase4.baseline_agent import TraceAgentOutput
from mbpp_pipeline.phase4.bridge import build_benchmark_data
from mbpp_pipeline.phase4.lean_builder import build_lean_file
from mbpp_pipeline.phase4.trace_agent import create_trace_agent
from mbpp_pipeline.phase5.report import PipelineReport
from mbpp_pipeline.phase5.verifier import PipelineVerifier, VerificationResult
from verina.benchmark.common import BenchmarkSpecEvaluationConfig


# ── Phase 1 ──────────────────────────────────────────────────────────────────


def run_phase1(cfg: PipelineConfig, *, limit: Optional[int] = None) -> List[MBPPEntry]:
    """Export and validate MBPP dataset."""
    entries = export_mbpp_to_jsonl(cfg.phase1.mbpp_cache_dir, cfg.phase1.output_file)
    valid = load_and_validate(entries)
    if limit:
        valid = valid[:limit]
        logger.info(f"Phase 1: limited to {len(valid)} entries")
    logger.info(f"Phase 1 complete: {len(valid)} valid entries")
    return valid


# ── Phase 2 ──────────────────────────────────────────────────────────────────


def run_phase2(cfg: PipelineConfig, *, limit: Optional[int] = None) -> List[MutatedEntry]:
    """Generate adversarial mutations."""
    entries = load_mbpp_jsonl(cfg.phase1.output_file)
    entries = load_and_validate(entries)
    if limit:
        entries = entries[:limit]

    mutated = build_adversarial_dataset(
        entries=entries,
        operator_names=cfg.phase2.mutation_operators,
        max_mutations_per_entry=cfg.phase2.max_mutations_per_entry,
        require_adversarial_filter=cfg.phase2.require_adversarial_filter,
        seed=cfg.phase2.seed,
    )

    save_mutated_entries(mutated, cfg.phase2.output_file)
    logger.info(f"Phase 2 complete: {len(mutated)} mutated entries")
    return mutated


# ── Phase 3 ──────────────────────────────────────────────────────────────────


async def run_phase3(cfg: PipelineConfig, *, limit: Optional[int] = None) -> List[SolverResult]:
    """Solve MBPP tasks with LLMs."""
    entries = load_mbpp_jsonl(cfg.phase1.output_file)
    entries = load_and_validate(entries)
    if limit:
        entries = entries[:limit]

    solver = TaskSolver(cfg.phase3)
    results = await solver.solve_batch(entries)

    save_solver_results(results, cfg.phase3.output_file)
    logger.info(
        f"Phase 3 complete: {len(results)} results, "
        f"{sum(1 for r in results if r.passes_tests)} passing"
    )
    return results


# ── Phase 4 ──────────────────────────────────────────────────────────────────


async def run_phase4(cfg: PipelineConfig, *, limit: Optional[int] = None) -> Dict[str, TraceAgentOutput]:
    """Auto-formalize solutions into Lean 4."""
    entries = load_mbpp_jsonl(cfg.phase1.output_file)
    entry_map: Dict[int, MBPPEntry] = {e.task_id: e for e in entries}

    solver_results = load_solver_results(cfg.phase3.output_file)

    # Only formalize entries that passed tests
    solver_results = [sr for sr in solver_results if sr.passes_tests and sr.generated_solution]
    if limit:
        solver_results = solver_results[:limit]
        logger.info(f"Phase 4: limited to {len(solver_results)} entries")

    agent = create_trace_agent(cfg.phase4)
    output_dir = Path(cfg.phase4.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, TraceAgentOutput] = {}
    semaphore = asyncio.Semaphore(cfg.max_workers)

    async def _process(sr: SolverResult) -> None:
        entry = entry_map.get(sr.task_id)
        if entry is None:
            logger.warning(f"No MBPP entry for task_id={sr.task_id}")
            return

        async with semaphore:
            try:
                output = await agent.run_full_pipeline(entry, sr)
                outputs[f"mbpp_{sr.task_id}"] = output

                # Write .lean file
                from mbpp_pipeline.phase4.bridge import mbpp_to_signature

                sig = mbpp_to_signature(entry, sr.generated_solution)
                lean_content = build_lean_file(
                    signature=sig,
                    imports=output.imports,
                    code_aux=output.code_aux,
                    code=output.code,
                    precond_aux=output.precond_aux,
                    precond=output.precond or "True",
                    postcond_aux=output.postcond_aux,
                    postcond=output.postcond,
                    proof_aux=output.proof_aux,
                    proof=output.proof,
                )
                lean_path = output_dir / f"mbpp_{sr.task_id}.lean"
                lean_path.write_text(lean_content)

                # Write metadata JSON
                meta_path = output_dir / f"mbpp_{sr.task_id}.json"
                meta_path.write_text(output.model_dump_json(indent=2))

                logger.info(f"Task {sr.task_id}: formalized (compile={output.compile_success})")

            except Exception as e:
                logger.error(f"Task {sr.task_id}: formalization failed: {e}")

    tasks = [_process(sr) for sr in solver_results]
    await asyncio.gather(*tasks)

    logger.info(
        f"Phase 4 complete: {len(outputs)} formalized, "
        f"{sum(1 for o in outputs.values() if o.compile_success)} compiling"
    )
    return outputs


# ── Phase 5 ──────────────────────────────────────────────────────────────────


async def run_phase5(cfg: PipelineConfig) -> PipelineReport:
    """Verify Lean artifacts via Verina's evaluation pipeline."""
    entries = load_mbpp_jsonl(cfg.phase1.output_file)
    entry_map: Dict[int, MBPPEntry] = {e.task_id: e for e in entries}

    solver_results = load_solver_results(cfg.phase3.output_file)
    sr_map: Dict[int, SolverResult] = {sr.task_id: sr for sr in solver_results}

    output_dir = Path(cfg.phase4.output_dir)
    eval_config = BenchmarkSpecEvaluationConfig(
        unit_test=cfg.phase5.eval_spec_config.unit_test,
        use_plausible_pass=cfg.phase5.eval_spec_config.use_plausible_pass,
    )
    verifier = PipelineVerifier(eval_config)

    results: List[VerificationResult] = []

    # Load all formalization outputs
    for meta_file in sorted(output_dir.glob("mbpp_*.json")):
        task_id_str = meta_file.stem  # e.g., "mbpp_11"
        try:
            with open(meta_file) as f:
                output = TraceAgentOutput.model_validate_json(f.read())
        except Exception as e:
            logger.error(f"Failed to load {meta_file}: {e}")
            continue

        # Extract task_id
        try:
            tid = int(task_id_str.split("_")[1])
        except (IndexError, ValueError):
            logger.warning(f"Cannot parse task_id from {meta_file.name}")
            continue

        entry = entry_map.get(tid)
        sr = sr_map.get(tid)
        if entry is None or sr is None:
            logger.warning(f"Missing entry/solver_result for task {tid}")
            continue

        data = build_benchmark_data(entry, sr)

        try:
            vr = await verifier.verify_full(data, output)
            results.append(vr)
        except Exception as e:
            logger.error(f"Task {tid}: verification failed: {e}")

    report = PipelineReport(results=results)
    report.compute_summary()
    report.save(cfg.phase5.output_file)

    if report.summary:
        logger.info(f"Phase 5 summary: {report.summary.to_dict()}")

    return report


# ── Full pipeline ────────────────────────────────────────────────────────────


async def run_all(cfg: PipelineConfig, *, limit: Optional[int] = None) -> PipelineReport:
    """Run the full pipeline: phases 1-5."""
    logger.info(f"Starting full pipeline{f' (limit={limit})' if limit else ''}")

    # Phase 1 (sync)
    run_phase1(cfg, limit=limit)

    # Phase 2 (sync)
    run_phase2(cfg, limit=limit)

    # Phase 3 (async)
    await run_phase3(cfg, limit=limit)

    # Phase 4 (async)
    await run_phase4(cfg, limit=limit)

    # Phase 5 (async)
    report = await run_phase5(cfg)

    logger.info("Full pipeline complete")
    return report
