"""Multi-model task solver for MBPP problems."""

import asyncio
from pathlib import Path

import dspy
from loguru import logger

from mbpp_pipeline.config import Phase3Config
from mbpp_pipeline.phase1.schema import MBPPEntry
from mbpp_pipeline.phase2.schema import MutatedEntry
from mbpp_pipeline.phase3.prompts import build_chat_prompt, extract_python_code
from mbpp_pipeline.phase3.schema import SolverResult
from mbpp_pipeline.utils.python_exec import safe_exec


class SolveMBPPSig(dspy.Signature):
    """Solve an MBPP Python programming task."""

    task_description = dspy.InputField(desc="Natural language description of the task")
    test_cases = dspy.InputField(desc="Test cases that the solution must pass")
    solution = dspy.OutputField(desc="Complete Python solution code")


SolveMBPPSig.__doc__ = """You are an expert Python programmer. Given a task description and test cases, write a complete Python solution that passes all tests. Output ONLY valid Python code."""


class TaskSolver:
    """Solves MBPP tasks using LLMs via DSPy or litellm."""

    def __init__(self, config: Phase3Config):
        self.config = config
        self.lm = config.solver_lm_config.get_model()

    def _build_test_string(self, entry: MBPPEntry | MutatedEntry) -> str:
        test_list = entry.test_list
        return "\n".join(test_list)

    async def solve_one(self, entry: MBPPEntry | MutatedEntry) -> SolverResult:
        """Solve a single MBPP entry."""
        is_mutated = isinstance(entry, MutatedEntry)
        task_id = entry.original_task_id if is_mutated else entry.task_id
        mutation_id = entry.mutation_id if is_mutated else None
        text = entry.text
        test_list = entry.test_list

        try:
            with dspy.context(lm=self.lm):
                if self.config.prompt_style == "chat":
                    generator = dspy.Predict(SolveMBPPSig)
                    response = await generator.acall(
                        task_description=text,
                        test_cases=self._build_test_string(entry),
                    )
                    raw_solution = response.solution
                else:
                    # FIM-style: use litellm directly
                    prompt = build_chat_prompt(text, test_list)
                    response = await generator.acall(
                        task_description=prompt,
                        test_cases="",
                    )
                    raw_solution = response.solution

            solution = extract_python_code(raw_solution)

            # Test the solution
            test_code = "\n".join(test_list)
            setup = ""
            if (isinstance(entry, MBPPEntry) and entry.test_setup_code) or (
                isinstance(entry, MutatedEntry) and entry.test_setup_code
            ):
                setup = entry.test_setup_code + "\n"
            passes, _ = safe_exec(solution, setup + test_code)

            return SolverResult(
                task_id=task_id,
                mutation_id=mutation_id,
                model_name=self.config.solver_lm_config.model_name,
                prompt_style=self.config.prompt_style,
                generated_solution=solution,
                passes_tests=passes,
                is_from_adversarial=is_mutated,
            )
        except Exception as e:
            logger.error(f"Task {task_id}: solver error: {e}")
            return SolverResult(
                task_id=task_id,
                mutation_id=mutation_id,
                model_name=self.config.solver_lm_config.model_name,
                prompt_style=self.config.prompt_style,
                generated_solution="",
                passes_tests=False,
                is_from_adversarial=is_mutated,
                error=str(e),
            )

    async def solve_batch(self, entries: list[MBPPEntry | MutatedEntry]) -> list[SolverResult]:
        """Solve a batch of MBPP entries with concurrency control."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def _limited(entry: MBPPEntry | MutatedEntry) -> SolverResult:
            async with semaphore:
                return await self.solve_one(entry)

        tasks = [_limited(e) for e in entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        solver_results: list[SolverResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                entry = entries[i]
                task_id = (
                    entry.original_task_id if isinstance(entry, MutatedEntry) else entry.task_id
                )
                solver_results.append(
                    SolverResult(
                        task_id=task_id,
                        model_name=self.config.solver_lm_config.model_name,
                        prompt_style=self.config.prompt_style,
                        generated_solution="",
                        passes_tests=False,
                        error=str(r),
                    )
                )
            else:
                solver_results.append(r)
        return solver_results


def save_solver_results(results: list[SolverResult], output_path: str | Path) -> None:
    """Write SolverResult list to JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(r.model_dump_json() + "\n")
    logger.info(f"Wrote {len(results)} solver results to {output_path}")


def load_solver_results(path: str | Path) -> list[SolverResult]:
    """Load SolverResult list from JSONL."""
    results: list[SolverResult] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(SolverResult.model_validate_json(line))
    return results
