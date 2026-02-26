from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional, Tuple

from src.state import Evidence


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _attr_chain(node: ast.AST) -> Optional[Tuple[str, ...]]:
    parts: List[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return tuple(reversed(parts))
    return None


def _is_base_model_subclass(class_def: ast.ClassDef) -> bool:
    for b in class_def.bases or []:
        chain = _attr_chain(b)
        if chain == ("BaseModel",) or chain == ("pydantic", "BaseModel"):
            return True
        if isinstance(b, ast.Name) and b.id == "BaseModel":
            return True
    return False


def _is_typeddict_subclass(class_def: ast.ClassDef) -> bool:
    for b in class_def.bases or []:
        chain = _attr_chain(b)
        if chain == ("TypedDict",) or chain == ("typing_extensions", "TypedDict"):
            return True
        if isinstance(b, ast.Name) and b.id == "TypedDict":
            return True
    return False


def _field_is_annotated_with(node: ast.AST, want_chain: Tuple[str, ...]) -> bool:
    """
    Detects: Annotated[T, operator.add] or Annotated[T, merge_evidence_dicts]
    where the reducer appears as a Name or an Attribute chain.
    """
    if not isinstance(node, ast.AnnAssign):
        return False
    ann = node.annotation
    if ann is None:
        return False
    if not isinstance(ann, ast.Subscript):
        return False

    base = _attr_chain(ann.value)
    if base not in {
        ("Annotated",),
        ("typing", "Annotated"),
        ("typing_extensions", "Annotated"),
    }:
        return False

    sl = ann.slice
    if isinstance(sl, ast.Tuple):
        meta_nodes = list(sl.elts[1:])
    else:
        meta_nodes = []

    for m in meta_nodes:
        chain = _attr_chain(m)
        if chain == want_chain:
            return True
        if isinstance(m, ast.Name) and (
            want_chain == (m.id,) or want_chain[-1] == m.id
        ):
            return True

    return False


def inspect_state_models(repo_path: str) -> List[Evidence]:
    root = Path(repo_path)
    state_py = root / "src" / "state.py"
    if not state_py.exists():
        return [
            Evidence(
                goal="state_management_rigor",
                found=False,
                content="src/state.py not found",
                location="src/state.py",
                rationale="State file missing",
                confidence=0.9,
            )
        ]

    txt = _read_text(state_py)
    try:
        tree = ast.parse(txt)
    except SyntaxError as e:
        return [
            Evidence(
                goal="state_management_rigor",
                found=False,
                content=f"SyntaxError parsing src/state.py: {e}",
                location="src/state.py",
                rationale="Could not parse state file via AST",
                confidence=0.9,
            )
        ]

    evidence_model = None
    judicial_model = None
    agent_state = None

    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "Evidence":
            evidence_model = n
        if isinstance(n, ast.ClassDef) and n.name == "JudicialOpinion":
            judicial_model = n
        if isinstance(n, ast.ClassDef) and n.name == "AgentState":
            agent_state = n

    evidence_is_base_model = bool(
        evidence_model and _is_base_model_subclass(evidence_model)
    )
    judicial_is_base_model = bool(
        judicial_model and _is_base_model_subclass(judicial_model)
    )
    agent_state_is_typeddict = bool(agent_state and _is_typeddict_subclass(agent_state))

    opinions_has_operator_add = False
    evidences_has_merge_or_ior = False

    if agent_state:
        for stmt in agent_state.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if stmt.target.id == "opinions":
                    opinions_has_operator_add = _field_is_annotated_with(
                        stmt, ("operator", "add")
                    )
                if stmt.target.id == "evidences":
                    evidences_has_merge_or_ior = _field_is_annotated_with(
                        stmt, ("operator", "ior")
                    ) or _field_is_annotated_with(stmt, ("merge_evidence_dicts",))

    found = (
        evidence_is_base_model
        and judicial_is_base_model
        and agent_state_is_typeddict
        and opinions_has_operator_add
        and evidences_has_merge_or_ior
    )

    content_lines: List[str] = [
        f"evidence_model_base_model={evidence_is_base_model}",
        f"judicial_opinion_base_model={judicial_is_base_model}",
        f"agent_state_typed_dict={agent_state_is_typeddict}",
        f"opinions_reducer_operator_add={opinions_has_operator_add}",
        f"evidences_reducer_operator_ior_or_merge={evidences_has_merge_or_ior}",
    ]

    return [
        Evidence(
            goal="state_management_rigor",
            found=found,
            content="\n".join(content_lines),
            location="src/state.py",
            rationale="AST inspection of state models and reducers",
            confidence=0.85 if found else 0.75,
        )
    ]
