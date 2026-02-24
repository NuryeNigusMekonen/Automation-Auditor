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
    node_names = set()

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            nonlocal stategraph_calls, add_edge_calls, add_conditional_calls, node_names

            fn_name = ""
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn_name = node.func.attr

            if fn_name == "StateGraph":
                stategraph_calls += 1
            if fn_name == "add_edge":
                add_edge_calls += 1
            if fn_name == "add_conditional_edges":
                add_conditional_calls += 1
            if fn_name == "add_node" and node.args:
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    node_names.add(node.args[0].value)

            self.generic_visit(node)

    CallVisitor().visit(tree)

    start_edge_targets = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_edge":
            if len(n.args) >= 2:
                a0, a1 = n.args[0], n.args[1]
                if isinstance(a0, ast.Name) and a0.id == "START":
                    if isinstance(a1, ast.Constant) and isinstance(a1.value, str):
                        start_edge_targets.append(a1.value)

    parallel_hint = len(set(start_edge_targets)) >= 2

    content_lines = [
        f"graph_file={graph_file}",
        f"StateGraph_calls={stategraph_calls}",
        f"add_edge_calls={add_edge_calls}",
        f"add_conditional_edges_calls={add_conditional_calls}",
        f"add_node_names={sorted(list(node_names))[:50]}",
        f"START_targets={sorted(list(set(start_edge_targets)))}",
        f"parallel_hint={parallel_hint}",
    ]

    found = stategraph_calls > 0 and add_edge_calls > 0

    return [
        Evidence(
            goal=goal,
            found=found,
            content="\n".join(content_lines),
            location=str(graph_file),
            rationale="AST inspection of graph wiring and parallel fan-out signal",
            confidence=0.9 if found else 0.75,
        )
    ]