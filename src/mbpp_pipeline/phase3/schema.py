"""Schema for Phase 3: LLM task solving."""

from typing import Optional

from pydantic import BaseModel, Field


class SolverResult(BaseModel):
    task_id: int = Field(description="MBPP task id (or original_task_id for mutations)")
    mutation_id: Optional[str] = Field(default=None, description="Mutation id if from adversarial set")
    model_name: str = Field(description="LLM model used")
    prompt_style: str = Field(description="'chat' or 'fim'")
    generated_solution: str = Field(description="Generated Python code")
    passes_tests: Optional[bool] = Field(default=None, description="Whether solution passes tests")
    is_from_adversarial: bool = Field(default=False, description="Whether from mutated dataset")
    error: Optional[str] = Field(default=None, description="Error if solving failed")
