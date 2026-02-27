from __future__ import annotations

import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Evidence(BaseModel):
    goal: str
    found: bool = Field(description="Whether the artifact exists")
    content: Optional[str] = None
    location: str = Field(description="File path, commit hash, or tool name")
    rationale: str = Field(description="Why you trust this evidence")
    confidence: float = Field(ge=0.0, le=1.0)


class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: List[str] = Field(default_factory=list)


def merge_evidence_dicts(
    left: Dict[str, List[Evidence]] | None,
    right: Dict[str, List[Evidence]] | None,
) -> Dict[str, List[Evidence]]:
    out: Dict[str, List[Evidence]] = {}
    if left:
        for k, v in left.items():
            out[k] = list(v or [])
    if right:
        for k, v in right.items():
            if k not in out:
                out[k] = list(v or [])
            else:
                out[k].extend(list(v or []))
    return out


class AgentState(TypedDict):
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]
    enable_vision: bool
    offline_mode: bool
    runtime_config: Dict
    workspace_dir: str

    evidences: Annotated[Dict[str, List[Evidence]], merge_evidence_dicts]
    opinions: Annotated[List[JudicialOpinion], operator.add]

    final_report: Optional[dict]
    final_report_markdown: str
