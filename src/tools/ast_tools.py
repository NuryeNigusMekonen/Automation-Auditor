from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional, Set, Tuple

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


def _const_str(n: ast.AST) -> Optional[str]:
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
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
                rationale="No graph.py found for StateGraph wiring inspection",
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
                location=str(graph_file.relative_to(Path(repo_path))),
                rationale="graph.py exists but was not readable",
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
                content=f"SyntaxError parsing graph.py: {e}",
                location=str(graph_file.relative_to(Path(repo_path))),
                rationale="AST parse failed",
                confidence=0.9,
            )
        ]

    stategraph_calls = 0
    add_edge_calls = 0
    add_conditional_calls = 0

    nodes: Set[str] = set()
    edges: List[Tuple[str, str]] = []
    start_targets: List[str] = []
    conditional_sources: Set[str] = set()

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            nonlocal stategraph_calls, add_edge_calls, add_conditional_calls
            fn = ""
            if isinstance(node.func, ast.Name):
                fn = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn = node.func.attr

            if fn == "StateGraph":
                stategraph_calls += 1

            if fn == "add_node" and node.args:
                name = _const_str(node.args[0])
                if name:
                    nodes.add(name)

            if fn == "add_edge":
                add_edge_calls += 1
                if len(node.args) >= 2:
                    a0 = node.args[0]
                    a1 = node.args[1]

                    src = None
                    if isinstance(a0, ast.Name) and a0.id == "START":
                        src = "START"
                    else:
                        src = _const_str(a0)

                    dst = _const_str(a1)

                    if src and dst:
                        edges.append((src, dst))
                        if src == "START":
                            start_targets.append(dst)

            if fn == "add_conditional_edges":
                add_conditional_calls += 1
                if node.args:
                    src = _const_str(node.args[0])
                    if src:
                        conditional_sources.add(src)

            self.generic_visit(node)

    V().visit(tree)

    uniq_start = sorted(set(start_targets))
    detectives = {"repo_investigator", "doc_analyst", "vision_inspector"}
    judges = {"prosecutor", "defense", "tech_lead"}
    aggregator = "evidence_aggregator"
    opinions_agg = "opinions_aggregator"
    cj = "chief_justice"

    has_detective_fanout = len([t for t in uniq_start if t in detectives]) >= 2
    has_evidence_agg = aggregator in nodes
    has_judge_fanout = any((aggregator, j) in edges for j in judges) or any(
        (j, opinions_agg) in edges for j in judges
    )
    has_fanin_to_cj = (opinions_agg in nodes) and (cj in nodes)

    has_conditionals = add_conditional_calls > 0

    found = stategraph_calls > 0 and add_edge_calls > 0

    content_lines: List[str] = []
    content_lines.append(f"graph_file={str(graph_file.relative_to(Path(repo_path)))}")
    content_lines.append(f"StateGraph_calls={stategraph_calls}")
    content_lines.append(f"add_edge_calls={add_edge_calls}")
    content_lines.append(f"add_conditional_edges_calls={add_conditional_calls}")
    content_lines.append(f"nodes={sorted(list(nodes))[:200]}")
    content_lines.append(f"START_targets={uniq_start}")
    content_lines.append(f"edges_sample={sorted(edges)[:60]}")
    content_lines.append(f"conditional_sources={sorted(list(conditional_sources))}")

    content_lines.append(f"signal_detective_fanout={has_detective_fanout}")
    content_lines.append(f"signal_evidence_aggregator={has_evidence_agg}")
    content_lines.append(f"signal_judge_parallelism={has_judge_fanout}")
    content_lines.append(f"signal_fanin_to_chief_justice={has_fanin_to_cj}")
    content_lines.append(f"signal_conditionals_present={has_conditionals}")

    base_ev = Evidence(
        goal=goal,
        found=found,
        content="\n".join(content_lines),
        location=str(graph_file.relative_to(Path(repo_path))),
        rationale="AST inspection of StateGraph nodes, edges, fan-out, fan-in, and conditional routing",
        confidence=0.9 if found else 0.75,
    )

    theory_lines = [
        f"fan_out_detectives={has_detective_fanout} targets={sorted([t for t in uniq_start if t in detectives])}",
        f"fan_in_detectives={has_evidence_agg} aggregator={aggregator}",
        f"fan_out_judges={has_judge_fanout} judges={sorted(list(judges))}",
        f"fan_in_judges={has_fanin_to_cj} opinions_aggregator={opinions_agg} chief_justice={cj}",
        f"conditional_edges_present={has_conditionals} sources={sorted(list(conditional_sources))}",
        "theory_mapping=Fan-Out->multiple START edges. Fan-In->aggregation nodes. Conditional edges->add_conditional_edges call sites.",
    ]
    theory_found = has_detective_fanout or has_judge_fanout or has_conditionals
    theory_ev = Evidence(
        goal="theoretical_depth",
        found=bool(theory_found),
        content="\n".join(theory_lines),
        location=str(graph_file.relative_to(Path(repo_path))),
        rationale="Mapped Fan-In, Fan-Out, and conditional routing to concrete AST signals",
        confidence=0.85 if theory_found else 0.7,
    )

    return [base_ev, theory_ev]
