"""Tree-sitter Python parser utilities."""

from functools import lru_cache

import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Tree


@lru_cache(maxsize=1)
def get_python_language() -> Language:
    """Return the tree-sitter Python language singleton."""
    return Language(tspython.language())


@lru_cache(maxsize=1)
def get_python_parser() -> Parser:
    """Return a tree-sitter Parser configured for Python."""
    parser = Parser(get_python_language())
    return parser


def parse_python(source: str) -> Tree:
    """Parse Python source code into a tree-sitter Tree."""
    parser = get_python_parser()
    return parser.parse(source.encode("utf-8"))
