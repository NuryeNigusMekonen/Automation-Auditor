## Goal
# Analyze graph structure.

## Checklist
# Parse python files
# Detect StateGraph usage, add_edge fan-out and fan-in patterns
# src/tools/ast_tools.py
from __future__ import annotations
import ast
import os
from typing import Dict, List, Set, Tuple


class GraphFacts(dict):
    pass


def _py_files_under(repo_path: str) -> List[str]:
    out: List[str] = []
    for root, _, files in os.walk(repo_path):
        for fn in files:
            if fn.endswith(".py"):
                out.append(os.path.join(root, fn))
    return out


def analyze_graph_structure(repo_path: str) -> GraphFacts:
    """
    AST-based checks for:
    - StateGraph instantiation
    - add_node calls
    - add_edge calls
    - fan-out presence (one source -> many destinations)
    - fan-in presence (many sources -> one destination)
    - conditional edge presence (add_conditional_edges)
    """
    stategraph_used = False
    add_node_calls: List[Tuple[str, int]] = []
    add_edge_calls: List[Tuple[str, int, str, str]] = []  # (file, lineno, src, dst)
    conditional_edges: List[Tuple[str, int]] = []

    for path in _py_files_under(repo_path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except Exception:
            continue

        for node in ast.walk(tree):
            # Detect StateGraph(...) call
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "StateGraph":
                    stategraph_used = True

            # Detect builder.add_node(...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "add_node":
                    add_node_calls.append((path, getattr(node, "lineno", -1)))
                if node.func.attr == "add_edge":
                    # Best-effort: edge args are usually (src, dst) or (START, "node")
                    src = _const_str(node.args[0]) if len(node.args) > 0 else ""
                    dst = _const_str(node.args[1]) if len(node.args) > 1 else ""
                    add_edge_calls.append((path, getattr(node, "lineno", -1), src, dst))
                if node.func.attr == "add_conditional_edges":
                    conditional_edges.append((path, getattr(node, "lineno", -1)))

    # Fan-out and fan-in
    out_map: Dict[str, Set[str]] = {}
    in_map: Dict[str, Set[str]] = {}
    for _, _, src, dst in add_edge_calls:
        if not src or not dst:
            continue
        out_map.setdefault(src, set()).add(dst)
        in_map.setdefault(dst, set()).add(src)

    fan_out_nodes = sorted([s for s, ds in out_map.items() if len(ds) >= 2])
    fan_in_nodes = sorted([d for d, ss in in_map.items() if len(ss) >= 2])

    return GraphFacts(
        stategraph_used=stategraph_used,
        add_node_count=len(add_node_calls),
        add_edge_count=len(add_edge_calls),
        fan_out_detected=bool(fan_out_nodes),
        fan_in_detected=bool(fan_in_nodes),
        fan_out_sources=fan_out_nodes,
        fan_in_targets=fan_in_nodes,
        conditional_edges_detected=bool(conditional_edges),
        samples={
            "edge_calls": add_edge_calls[:20],
            "conditional_edges": conditional_edges[:20],
        },
    )


def _const_str(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return ""