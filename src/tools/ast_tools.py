# src/tools/ast_tools.py
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

from src.state import Evidence


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")
    except FileNotFoundError:
        return None


def _find_graph_file(repo_path: str) -> Optional[Path]:
    root = Path(repo_path)

    candidates = [
        root / "src" / "graph.py",
        root / "graph.py",
        root / "app" / "graph.py",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c

    for p in root.rglob("graph.py"):
        sp = str(p)
        if "/.venv/" in sp or "/venv/" in sp or "__pycache__" in sp:
            continue
        return p

    return None


def analyze_graph_structure(repo_path: str) -> List[Evidence]:
    goal = "graph_orchestration"

    graph_file = _find_graph_file(repo_path)
    if not graph_file:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location="repo",
                rationale="No graph.py file found to inspect StateGraph wiring",
                confidence=0.95,
            )
        ]

    text = _read_text(graph_file)
    if text is None:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location=str(graph_file),
                rationale="graph.py exists but could not be read",
                confidence=0.8,
            )
        ]

    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=f"SyntaxError parsing {graph_file.name}: {e}",
                location=str(graph_file),
                rationale="Could not AST parse graph file",
                confidence=0.9,
            )
        ]

    stategraph_calls = 0
    add_edge_calls = 0
    add_conditional_calls = 0
    add_node_names: set[str] = set()

    start_edge_targets: list[str] = []
    conditional_sources: set[str] = set()

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            nonlocal stategraph_calls, add_edge_calls, add_conditional_calls, add_node_names
            nonlocal start_edge_targets, conditional_sources

            fn_name = ""
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn_name = node.func.attr

            if fn_name == "StateGraph":
                stategraph_calls += 1

            if fn_name == "add_edge":
                add_edge_calls += 1
                if len(node.args) >= 2:
                    a0, a1 = node.args[0], node.args[1]
                    if isinstance(a0, ast.Name) and a0.id == "START":
                        if isinstance(a1, ast.Constant) and isinstance(a1.value, str):
                            start_edge_targets.append(a1.value)

            if fn_name == "add_conditional_edges":
                add_conditional_calls += 1
                if node.args:
                    src = node.args[0]
                    if isinstance(src, ast.Constant) and isinstance(src.value, str):
                        conditional_sources.add(src.value)

            if fn_name == "add_node" and node.args:
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    add_node_names.add(a0.value)

            self.generic_visit(node)

    CallVisitor().visit(tree)

    parallel_hint = len(set(start_edge_targets)) >= 2

    # extra: look for routing helpers in the file (heuristic)
    defined_functions: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            defined_functions.add(n.name)

    found = stategraph_calls > 0 and add_edge_calls > 0

    content_lines = [
        f"graph_file={graph_file}",
        f"StateGraph_calls={stategraph_calls}",
        f"add_edge_calls={add_edge_calls}",
        f"add_conditional_edges_calls={add_conditional_calls}",
        f"add_node_names={sorted(list(add_node_names))[:100]}",
        f"START_targets={sorted(list(set(start_edge_targets)))}",
        f"parallel_hint={parallel_hint}",
        f"conditional_sources={sorted(list(conditional_sources))}",
        f"routing_helpers={sorted([n for n in defined_functions if 'route' in n.lower()])}",
    ]

    return [
        Evidence(
            goal=goal,
            found=found,
            content="\n".join(content_lines),
            location=str(graph_file),
            rationale="AST inspection of StateGraph wiring, fan-out, and conditional routing signals",
            confidence=0.9 if found else 0.75,
        )
    ]