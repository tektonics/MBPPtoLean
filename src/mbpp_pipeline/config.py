"""Pipeline configuration loaded from TOML."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field
from verina.utils.lm import LMConfig


class Phase1Config(BaseModel):
    mbpp_cache_dir: str = "data/mbpp_cache"
    output_file: str = "data/mbpp_full.jsonl"


class Phase2Config(BaseModel):
    max_mutations_per_entry: int = 3
    mutation_operators: list[str] = Field(
        default_factory=lambda: [
            "rename_variable",
            "remove_type_annotation",
            "rename_user_type",
            "rename_builtin_type",
        ]
    )
    require_adversarial_filter: bool = False
    output_file: str = "data/mbpp_mutated.jsonl"
    seed: int = 42


class Phase3Config(BaseModel):
    prompt_style: str = "chat"
    output_file: str = "data/solver_results.jsonl"
    max_concurrent: int = 16
    solver_lm_config: LMConfig = LMConfig(provider="openai", model_name="gpt-4o")


class DebugConfig(BaseModel):
    max_iterations: int = 10


class ImproveConfig(BaseModel):
    max_iterations: int = 3
    min_score_threshold: int = 7


class Phase4Config(BaseModel):
    dspy_module: str = "Predict"
    output_dir: str = "data/lean_artifacts"
    baseline_lm_config: LMConfig = LMConfig(provider="openai", model_name="o4-mini")
    judge_lm_config: LMConfig = LMConfig(
        provider="anthropic", model_name="claude-3-5-sonnet-20241022"
    )
    debug_config: DebugConfig = DebugConfig()
    improve_config: ImproveConfig = ImproveConfig()


class EvalSpecConfig(BaseModel):
    unit_test: bool = True
    use_plausible_pass: bool = True


class Phase5Config(BaseModel):
    output_file: str = "data/verification_report.json"
    eval_spec_config: EvalSpecConfig = EvalSpecConfig()


class PipelineConfig(BaseModel):
    output_dir: str = "data"
    max_workers: int = 16
    verina_root: str = "./verina"

    phase1: Phase1Config = Phase1Config()
    phase2: Phase2Config = Phase2Config()
    phase3: Phase3Config = Phase3Config()
    phase4: Phase4Config = Phase4Config()
    phase5: Phase5Config = Phase5Config()

    @staticmethod
    def from_toml(config_path: str | Path) -> "PipelineConfig":
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return PipelineConfig.model_validate(data)
