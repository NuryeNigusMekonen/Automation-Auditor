import ast
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GraphStructure:
    stategraph_used: bool
    add_edge_calls: int
    add_conditional_edges_calls: int
    start_fanout_edges: int
    has_aggregator_node: bool
    notes: str


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _get_call_attr_name(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def analyze_graph_structure(graph_py_text: str) -> GraphStructure:
    tree = ast.parse(graph_py_text)

    stategraph_used = False
    add_edge_calls = 0
    add_conditional_edges_calls = 0
    start_fanout_edges = 0
    has_aggregator_node = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            attr = _get_call_attr_name(node)
            if attr == "StateGraph":
                stategraph_used = True
            if attr == "add_edge":
                add_edge_calls += 1
                # crude fan-out heuristic: edge from START constant/name
                if len(node.args) >= 2 and _is_name(node.args[0], "START"):
                    start_fanout_edges += 1
            if attr == "add_conditional_edges":
                add_conditional_edges_calls += 1

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "EvidenceAggregator" in node.value or "evidence_aggregator" in node.value:
                has_aggregator_node = True

    notes = (
        f"stategraph_used={stategraph_used}, "
        f"add_edge_calls={add_edge_calls}, "
        f"add_conditional_edges_calls={add_conditional_edges_calls}, "
        f"start_fanout_edges={start_fanout_edges}, "
        f"has_aggregator_node={has_aggregator_node}"
    )

    return GraphStructure(
        stategraph_used=stategraph_used,
        add_edge_calls=add_edge_calls,
        add_conditional_edges_calls=add_conditional_edges_calls,
        start_fanout_edges=start_fanout_edges,
        has_aggregator_node=has_aggregator_node,
        notes=notes,
    )


def find_pydantic_and_reducers(state_py_text: str) -> Dict[str, bool]:
    tree = ast.parse(state_py_text)
    found_basemodel = False
    found_typeddict = False
    found_operator_add = False
    found_operator_ior = False
    found_annotated = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "BaseModel":
            found_basemodel = True
        if isinstance(node, ast.Name) and node.id == "TypedDict":
            found_typeddict = True
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "operator":
            if node.attr == "add":
                found_operator_add = True
            if node.attr == "ior":
                found_operator_ior = True
        if isinstance(node, ast.Name) and node.id == "Annotated":
            found_annotated = True

    return {
        "pydantic_basemodel": found_basemodel,
        "typeddict": found_typeddict,
        "annotated": found_annotated,
        "operator_add": found_operator_add,
        "operator_ior": found_operator_ior,
    }