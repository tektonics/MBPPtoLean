"""Centralized logging configuration using loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(  # A
    log_dir: str = "data/logs",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """Configure loguru with file and console sinks.

    Args:
        log_dir: Directory for log files.
        level: Minimum log level.
        rotation: Log file rotation size.
        retention: How long to keep old log files.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler (concise)
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # File handler (verbose, structured)
    logger.add(
        str(log_path / "pipeline_{time}.log"),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=rotation,
        retention=retention,
        serialize=False,
    )

    # JSON log for machine parsing
    logger.add(
        str(log_path / "pipeline_{time}.jsonl"),
        level="DEBUG",
        serialize=True,
        rotation=rotation,
        retention=retention,
    )

    logger.info("Logging initialized", log_dir=log_dir, level=level)
