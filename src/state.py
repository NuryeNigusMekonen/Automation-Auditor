##  Goal
#Define typed models and shared state.

##  Checklist
#Evidence, Pydantic BaseModel
#JudicialOpinion, Pydantic BaseModel
#AgentState, TypedDict with reducers
#
##  Output
#You can import AgentState from src.state without errors.
# src/state.py
import operator
from typing import Annotated, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Evidence(BaseModel):
    goal: str = Field(description="What this evidence was trying to verify")
    found: bool = Field(description="Whether the artifact / property was found")
    content: Optional[str] = Field(default=None, description="Short snippet or extracted text")
    location: str = Field(description="File path, commit hash, or other location pointer")
    rationale: str = Field(description="Why you trust this evidence")
    confidence: float = Field(ge=0.0, le=1.0)


class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: List[str] = Field(default_factory=list)


class AgentState(TypedDict):
    repo_url: str
    pdf_path: str
    out_path: str
    rubric_dimensions: List[Dict]

    # Reducers prevent overwrites during parallel execution
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
    opinions: Annotated[List[JudicialOpinion], operator.add]

    # Internal runtime fields
    workdir: str
    repo_local_path: str
    repo_commit_sha: str

    final_report: str