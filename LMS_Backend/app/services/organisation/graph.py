"""Graph helpers for parent/child structures (pure; no database).

Edges are ``(child, parent)`` pairs. A unit may have several parents over time, so
cycle checks treat every edge that overlaps the period of interest as present at
once. This is conservative: it can refuse a link whose would-be cycle only exists
across non-overlapping dates, but it never lets a real cycle through.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping


def creates_cycle(edges: Iterable[tuple[int, int]], child: int, parent: int) -> bool:
    """Would adding ``child -> parent`` close a cycle (or link a node to itself)?"""
    if child == parent:
        return True
    parents: dict[int, set[int]] = defaultdict(set)
    for edge_child, edge_parent in edges:
        parents[edge_child].add(edge_parent)
    stack = [parent]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if node == child:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(parents.get(node, ()))
    return False


def ancestor_path(node: int, parent_of: Mapping[int, int]) -> list[int]:
    """Ancestors of ``node`` from the root down to its parent (single parent per node)."""
    path: list[int] = []
    seen = {node}
    current = parent_of.get(node)
    while current is not None and current not in seen:
        path.append(current)
        seen.add(current)
        current = parent_of.get(current)
    path.reverse()
    return path


def descendants(root: int, parent_of: Mapping[int, int]) -> set[int]:
    """All nodes below ``root`` (excluding it) in a single-parent snapshot."""
    children: dict[int, list[int]] = defaultdict(list)
    for child, parent in parent_of.items():
        children[parent].append(child)
    result: set[int] = set()
    stack = list(children.get(root, ()))
    while stack:
        node = stack.pop()
        if node in result or node == root:
            continue
        result.add(node)
        stack.extend(children.get(node, ()))
    return result
