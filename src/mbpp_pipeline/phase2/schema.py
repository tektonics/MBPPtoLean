"""Schema for Phase 2: Adversarial mutations."""

from enum import StrEnum

from pydantic import BaseModel, Field

from mbpp_pipeline.phase1.schema import MBPPEntry


class MutationType(StrEnum):
    RENAME_VARIABLE = "rename_variable"
    REMOVE_TYPE_ANNOTATION = "remove_type_annotation"
    RENAME_USER_TYPE = "rename_user_type"
    RENAME_BUILTIN_TYPE = "rename_builtin_type"


class MutationRecord(BaseModel):
    mutation_type: MutationType
    original: str = Field(description="Original text that was mutated")
    replacement: str = Field(description="Replacement text")
    location: str | None = Field(default=None, description="Location in AST")


class MutatedEntry(BaseModel):
    original_task_id: int
    mutation_id: str = Field(description="Unique id e.g. '11_rename_variable_0'")
    text: str
    original_code: str
    mutated_code: str
    test_list: list[str]
    test_setup_code: str = ""
    challenge_test_list: list[str] = Field(default_factory=list)
    mutations_applied: list[MutationRecord] = Field(default_factory=list)
    tests_pass_on_mutated: bool | None = None

    @staticmethod
    def from_mbpp_entry(
        entry: MBPPEntry,
        mutated_code: str,
        mutation_id: str,
        mutations: list[MutationRecord],
    ) -> "MutatedEntry":
        return MutatedEntry(
            original_task_id=entry.task_id,
            mutation_id=mutation_id,
            text=entry.text,
            original_code=entry.code,
            mutated_code=mutated_code,
            test_list=entry.test_list,
            test_setup_code=entry.test_setup_code,
            challenge_test_list=entry.challenge_test_list,
            mutations_applied=mutations,
        )
