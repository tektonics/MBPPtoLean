"""Pydantic models for MBPP dataset entries."""

from typing import List

from pydantic import BaseModel, Field


class MBPPEntry(BaseModel):
    task_id: int = Field(description="MBPP task identifier")
    text: str = Field(description="Natural language task description")
    code: str = Field(description="Reference Python solution")
    test_list: List[str] = Field(description="List of assert-based test strings")
    test_setup_code: str = Field(default="", description="Setup code for tests")
    challenge_test_list: List[str] = Field(
        default_factory=list, description="Challenge test strings"
    )
