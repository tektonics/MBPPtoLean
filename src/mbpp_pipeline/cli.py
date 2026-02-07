"""Typer CLI entry point for the MBPP Lean pipeline."""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger

from mbpp_pipeline.config import PipelineConfig

app = typer.Typer(name="mbpp-pipeline", help="MBPP → Lean 4 adversarial autoformalization pipeline")


@app.command()
def export(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max entries to process"),
) -> None:
    """Phase 1: Export MBPP dataset to JSONL."""
    cfg = PipelineConfig.from_toml(config_path)
    from mbpp_pipeline.runner import run_phase1

    run_phase1(cfg, limit=limit)
    logger.info("Phase 1 (export) complete.")


@app.command()
def mutate(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max entries to process"),
) -> None:
    """Phase 2: Generate adversarial mutations."""
    cfg = PipelineConfig.from_toml(config_path)
    from mbpp_pipeline.runner import run_phase2

    run_phase2(cfg, limit=limit)
    logger.info("Phase 2 (mutate) complete.")


@app.command()
def solve(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max entries to process"),
) -> None:
    """Phase 3: Solve tasks with LLMs."""
    cfg = PipelineConfig.from_toml(config_path)
    import asyncio

    from mbpp_pipeline.runner import run_phase3

    asyncio.run(run_phase3(cfg, limit=limit))
    logger.info("Phase 3 (solve) complete.")


@app.command()
def formalize(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max entries to formalize"),
) -> None:
    """Phase 4: Auto-formalize solutions to Lean 4."""
    cfg = PipelineConfig.from_toml(config_path)
    import asyncio

    from mbpp_pipeline.runner import run_phase4

    asyncio.run(run_phase4(cfg, limit=limit))
    logger.info("Phase 4 (formalize) complete.")


@app.command()
def verify(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
) -> None:
    """Phase 5: Verify Lean artifacts via Verina."""
    cfg = PipelineConfig.from_toml(config_path)
    import asyncio

    from mbpp_pipeline.runner import run_phase5

    asyncio.run(run_phase5(cfg))
    logger.info("Phase 5 (verify) complete.")


@app.command()
def run(
    config_path: Path = typer.Argument(..., help="Path to pipeline TOML config"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max entries to process per phase"),
) -> None:
    """Run the full pipeline (phases 1-5)."""
    cfg = PipelineConfig.from_toml(config_path)
    import asyncio

    from mbpp_pipeline.runner import run_all

    asyncio.run(run_all(cfg, limit=limit))
    logger.info("Full pipeline complete.")


if __name__ == "__main__":
    app()
