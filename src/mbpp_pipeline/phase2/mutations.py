"""Tree-sitter based mutation operators for Python code."""

from abc import ABC, abstractmethod
from random import Random
from typing import List, Tuple

from tree_sitter import Node, Tree

from mbpp_pipeline.phase2.schema import MutationRecord, MutationType
from mbpp_pipeline.utils.treesitter import parse_python

# Common variable name pool for renaming
_VAR_NAMES = [
    "val", "arg", "param", "item", "elem", "data", "obj", "tmp",
    "inp", "res", "acc", "cur", "prev", "nxt", "idx", "cnt",
]

# Builtin type aliases
_BUILTIN_TYPES = {"int", "float", "str", "bool", "list", "dict", "set", "tuple"}


class MutationOperator(ABC):
    """Base class for tree-sitter based mutation operators."""

    @abstractmethod
    def apply(
        self, source: str, tree: Tree, rng: Random
    ) -> Tuple[str, List[MutationRecord]]:
        """Apply mutation to source code.

        Returns:
            (mutated_source, list_of_mutation_records)
        """
        ...


def _collect_nodes(node: Node, type_name: str) -> List[Node]:
    """Recursively collect all nodes of a given type."""
    results: List[Node] = []
    if node.type == type_name:
        results.append(node)
    for child in node.children:
        results.extend(_collect_nodes(child, type_name))
    return results


def _replace_ranges(source: str, replacements: List[Tuple[int, int, str]]) -> str:
    """Apply byte-range replacements to source (sorted descending to preserve offsets)."""
    source_bytes = source.encode("utf-8")
    for start, end, new_text in sorted(replacements, key=lambda r: r[0], reverse=True):
        source_bytes = source_bytes[:start] + new_text.encode("utf-8") + source_bytes[end:]
    return source_bytes.decode("utf-8")


class RenameVariableOperator(MutationOperator):
    """Rename function/method parameter identifiers."""

    def apply(
        self, source: str, tree: Tree, rng: Random
    ) -> Tuple[str, List[MutationRecord]]:
        records: List[MutationRecord] = []

        # Find all function definitions
        func_nodes = _collect_nodes(tree.root_node, "function_definition")
        if not func_nodes:
            return source, records

        func_node = rng.choice(func_nodes)
        params_node = func_node.child_by_field_name("parameters")
        if params_node is None:
            return source, records

        # Collect parameter identifiers (skip self)
        param_ids: List[Node] = []
        for child in params_node.children:
            if child.type == "identifier" and child.text.decode() != "self":
                param_ids.append(child)
            elif child.type == "typed_parameter":
                name_node = child.child_by_field_name("name") or child.children[0]
                if name_node.type == "identifier" and name_node.text.decode() != "self":
                    param_ids.append(name_node)

        if not param_ids:
            return source, records

        target = rng.choice(param_ids)
        old_name = target.text.decode()
        new_name = rng.choice([n for n in _VAR_NAMES if n != old_name] or _VAR_NAMES)

        # Find all identifier references within the function body
        body_node = func_node.child_by_field_name("body")
        if body_node is None:
            return source, records

        refs = _collect_nodes(body_node, "identifier")
        refs = [r for r in refs if r.text.decode() == old_name]

        replacements: List[Tuple[int, int, str]] = [
            (target.start_byte, target.end_byte, new_name)
        ]
        for ref in refs:
            replacements.append((ref.start_byte, ref.end_byte, new_name))

        mutated = _replace_ranges(source, replacements)
        records.append(
            MutationRecord(
                mutation_type=MutationType.RENAME_VARIABLE,
                original=old_name,
                replacement=new_name,
                location=f"function:{func_node.child_by_field_name('name').text.decode() if func_node.child_by_field_name('name') else '?'}",
            )
        )
        return mutated, records


class RemoveTypeAnnotationOperator(MutationOperator):
    """Strip type annotations from function parameters and return types."""

    def apply(
        self, source: str, tree: Tree, rng: Random
    ) -> Tuple[str, List[MutationRecord]]:
        records: List[MutationRecord] = []

        func_nodes = _collect_nodes(tree.root_node, "function_definition")
        if not func_nodes:
            return source, records

        replacements: List[Tuple[int, int, str]] = []

        for func_node in func_nodes:
            # Remove return type annotation
            return_type = func_node.child_by_field_name("return_type")
            if return_type is not None:
                # Find the -> token before the return type
                for i, child in enumerate(func_node.children):
                    if child.type == "->" or (child.type == "type" and child == return_type):
                        # Remove from -> to end of return type
                        arrow_node = None
                        for c in func_node.children:
                            if c.type == "->":
                                arrow_node = c
                                break
                        if arrow_node:
                            replacements.append(
                                (arrow_node.start_byte, return_type.end_byte, "")
                            )
                            records.append(
                                MutationRecord(
                                    mutation_type=MutationType.REMOVE_TYPE_ANNOTATION,
                                    original=f"-> {return_type.text.decode()}",
                                    replacement="",
                                    location="return_type",
                                )
                            )
                        break

            # Remove typed_parameter annotations
            params_node = func_node.child_by_field_name("parameters")
            if params_node is None:
                continue
            typed_params = _collect_nodes(params_node, "typed_parameter")
            for tp in typed_params:
                name_node = tp.children[0] if tp.children else None
                if name_node is None:
                    continue
                param_name = name_node.text.decode()
                if param_name == "self":
                    continue
                # Replace the whole typed_parameter with just the name
                replacements.append((tp.start_byte, tp.end_byte, param_name))
                records.append(
                    MutationRecord(
                        mutation_type=MutationType.REMOVE_TYPE_ANNOTATION,
                        original=tp.text.decode(),
                        replacement=param_name,
                        location="parameter",
                    )
                )

        if not replacements:
            return source, records

        mutated = _replace_ranges(source, replacements)
        return mutated, records


class RenameUserTypeOperator(MutationOperator):
    """Rename user-defined class names and propagate references."""

    def apply(
        self, source: str, tree: Tree, rng: Random
    ) -> Tuple[str, List[MutationRecord]]:
        records: List[MutationRecord] = []

        class_nodes = _collect_nodes(tree.root_node, "class_definition")
        if not class_nodes:
            return source, records

        target_class = rng.choice(class_nodes)
        name_node = target_class.child_by_field_name("name")
        if name_node is None:
            return source, records

        old_name = name_node.text.decode()
        new_name = f"My{old_name}" if not old_name.startswith("My") else f"{old_name}V2"

        # Find all identifier references to this class name
        all_ids = _collect_nodes(tree.root_node, "identifier")
        refs = [n for n in all_ids if n.text.decode() == old_name]

        replacements = [(r.start_byte, r.end_byte, new_name) for r in refs]
        mutated = _replace_ranges(source, replacements)
        records.append(
            MutationRecord(
                mutation_type=MutationType.RENAME_USER_TYPE,
                original=old_name,
                replacement=new_name,
            )
        )
        return mutated, records


class RenameBuiltinTypeOperator(MutationOperator):
    """Insert aliases for builtin types and replace annotation-only references."""

    def apply(
        self, source: str, tree: Tree, rng: Random
    ) -> Tuple[str, List[MutationRecord]]:
        records: List[MutationRecord] = []

        # Scan for builtin type references in annotations
        all_ids = _collect_nodes(tree.root_node, "identifier")
        builtin_refs = [
            n for n in all_ids
            if n.text.decode() in _BUILTIN_TYPES and _is_annotation_context(n)
        ]

        if not builtin_refs:
            return source, records

        # Pick one builtin type to alias
        target = rng.choice(builtin_refs)
        old_type = target.text.decode()
        alias_name = f"My{old_type.capitalize()}"

        # Collect all annotation references to this type
        refs = [
            n for n in builtin_refs if n.text.decode() == old_type
        ]

        # Build alias line
        alias_line = f"{alias_name} = {old_type}\n"

        replacements = [(r.start_byte, r.end_byte, alias_name) for r in refs]
        mutated = _replace_ranges(source, replacements)
        mutated = alias_line + mutated

        records.append(
            MutationRecord(
                mutation_type=MutationType.RENAME_BUILTIN_TYPE,
                original=old_type,
                replacement=alias_name,
            )
        )
        return mutated, records


def _is_annotation_context(node: Node) -> bool:
    """Check if a node is in a type-annotation context."""
    parent = node.parent
    if parent is None:
        return False
    if parent.type in ("type", "typed_parameter", "function_definition"):
        return True
    if parent.type == "subscript" and parent.parent and parent.parent.type in ("type", "typed_parameter"):
        return True
    return _is_annotation_context(parent) if parent.type in ("subscript", "attribute") else False


OPERATOR_REGISTRY = {
    "rename_variable": RenameVariableOperator,
    "remove_type_annotation": RemoveTypeAnnotationOperator,
    "rename_user_type": RenameUserTypeOperator,
    "rename_builtin_type": RenameBuiltinTypeOperator,
}
