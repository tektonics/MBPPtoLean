"""Safe Python execution sandbox using subprocess."""

import subprocess
import textwrap
from typing import Tuple


def safe_exec(code: str, test_code: str, timeout: int = 10) -> Tuple[bool, str]:
    """Execute Python code + tests in a subprocess sandbox.

    Args:
        code: The Python code to execute (function definitions etc.).
        test_code: Test assertions to run after the code.
        timeout: Maximum execution time in seconds.

    Returns:
        (passed, output): Whether all tests passed, and stdout/stderr.
    """
    full_code = code + "\n\n" + test_code
    try:
        result = subprocess.run(
            ["python3", "-c", full_code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return passed, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Execution timed out after {timeout}s"
    except Exception as e:
        return False, f"Execution error: {e}"
