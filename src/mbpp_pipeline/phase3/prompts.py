"""Prompt templates for LLM task solving."""

import re
from typing import List, Optional

# FIM tokens per model family
FIM_TOKENS = {
    "codellama": {"prefix": "<PRE>", "suffix": "<SUF>", "middle": "<MID>"},
    "starcoder": {"prefix": "<fim_prefix>", "suffix": "<fim_suffix>", "middle": "<fim_middle>"},
    "deepseek": {"prefix": "<|fim▁begin|>", "suffix": "<|fim▁hole|>", "middle": "<|fim▁end|>"},
    "qwen": {"prefix": "<|fim_prefix|>", "suffix": "<|fim_suffix|>", "middle": "<|fim_middle|>"},
}


def build_chat_prompt(text: str, test_list: List[str]) -> str:
    """Build a chat-style prompt for MBPP task solving."""
    tests_str = "\n".join(test_list)
    return f"""You are an expert Python programmer. Solve the following task.

## Task
{text}

## Tests that must pass
```python
{tests_str}
```

## Instructions
- Write a complete Python solution that passes all the tests above.
- Output ONLY the Python code, no explanations.
- Do not include the test cases in your solution.
"""


def build_fim_prompt(
    text: str,
    prefix: str,
    suffix: str,
    model_family: str = "codellama",
) -> str:
    """Build a Fill-in-the-Middle prompt for code completion models."""
    tokens = FIM_TOKENS.get(model_family, FIM_TOKENS["codellama"])
    return f"{tokens['prefix']}{prefix}{tokens['suffix']}{suffix}{tokens['middle']}"


def extract_python_code(response: str) -> str:
    """Extract Python code from an LLM response, handling markdown fences."""
    # Try to extract from ```python ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        return matches[0].strip()

    # If no fences found, strip any leading/trailing markdown artifacts
    lines = response.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()
