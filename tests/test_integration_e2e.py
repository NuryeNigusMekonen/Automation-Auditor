from __future__ import annotations

import subprocess
from pathlib import Path

from pypdf import PdfWriter

from src.graph import build_graph
from src.state import JudicialOpinion


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_local_repo(repo_dir: Path) -> None:
    _write_text(
        repo_dir / "src" / "state.py",
        """
from typing import Annotated, Dict, List
import operator
from pydantic import BaseModel

class Evidence(BaseModel):
    goal: str
    found: bool
    location: str
    rationale: str
    confidence: float

class AgentState(dict):
    evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
""".strip()
        + "\n",
    )

    _write_text(
        repo_dir / "src" / "graph.py",
        """
from langgraph.graph import START, END, StateGraph

def build_graph(state_type):
    g = StateGraph(state_type)
    g.add_node("repo_investigator", lambda s: {})
    g.add_node("doc_analyst", lambda s: {})
    g.add_node("vision_inspector", lambda s: {})
    g.add_node("evidence_aggregator", lambda s: {})
    g.add_node("prosecutor", lambda s: {})
    g.add_node("defense", lambda s: {})
    g.add_node("tech_lead", lambda s: {})
    g.add_node("opinions_aggregator", lambda s: {})
    g.add_node("chief_justice", lambda s: {})

    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")
    g.add_edge("evidence_aggregator", "prosecutor")
    g.add_edge("evidence_aggregator", "defense")
    g.add_edge("evidence_aggregator", "tech_lead")
    g.add_edge("prosecutor", "opinions_aggregator")
    g.add_edge("defense", "opinions_aggregator")
    g.add_edge("tech_lead", "opinions_aggregator")
    g.add_edge("opinions_aggregator", "chief_justice")
    g.add_edge("chief_justice", END)
""".strip()
        + "\n",
    )

    _write_text(repo_dir / "src" / "nodes" / "judges.py", "def run():\n    return True\n")
    _write_text(repo_dir / "src" / "nodes" / "justice.py", "def run():\n    return True\n")
    _write_text(
        repo_dir / "src" / "tools" / "safe.py",
        "import subprocess\nsubprocess.run(['echo', 'ok'], check=False)\n",
    )

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "CI Bot"], cwd=repo_dir, check=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)


def _make_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as f:
        writer.write(f)


class _FakeLLM:
    def with_structured_output(self, *_args, **_kwargs):
        return self

    def invoke(self, prompt: str) -> JudicialOpinion:
        criterion_line = [x for x in prompt.splitlines() if x.startswith("Criterion id:")][0]
        criterion_id = criterion_line.split(":", 1)[1].strip()
        return JudicialOpinion(
            judge="Defense",
            criterion_id=criterion_id,
            score=4,
            argument="risk effort maintainability",
            cited_evidence=["src/graph.py"],
        )


def test_end_to_end_graph_with_local_fixture_repo_and_pdf(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    _init_local_repo(repo_dir)

    pdf_path = tmp_path / "tiny.pdf"
    _make_pdf(pdf_path)

    monkeypatch.setattr("src.nodes.detectives.clone_repo_sandboxed", lambda _url, _work: str(repo_dir))
    monkeypatch.setattr("src.nodes.judges._judge_llm", lambda: _FakeLLM())

    rubric_dimensions = [
        {
            "id": "git_forensic_analysis",
            "name": "Git Forensic Analysis",
            "forensic_instruction": "Inspect git history",
            "success_pattern": "iterative commits",
            "failure_pattern": "single bulk commit",
        },
        {
            "id": "graph_orchestration",
            "name": "Graph Orchestration",
            "forensic_instruction": "Inspect graph architecture",
            "success_pattern": "parallel fan-out and fan-in",
            "failure_pattern": "linear chain",
        },
        {
            "id": "safe_tool_engineering",
            "name": "Safe Tool Engineering",
            "forensic_instruction": "Inspect shell execution safety",
            "success_pattern": "no shell=True and no os.system",
            "failure_pattern": "unsafe shell execution",
        },
    ]

    graph = build_graph()
    out_state = graph.invoke(
        {
            "repo_url": "https://github.com/example/repo.git",
            "pdf_path": str(pdf_path),
            "rubric_dimensions": rubric_dimensions,
            "enable_vision": False,
            "workspace_dir": str(tmp_path / "work"),
            "evidences": {},
            "opinions": [],
            "final_report": None,
            "final_report_markdown": "",
        }
    )

    report = out_state.get("final_report_markdown", "")
    assert "# Audit Report" in report
    assert "## Executive Summary" in report
    assert out_state["final_report"]["overall_score"] >= 1.0
    assert out_state["final_report"]["overall_score"] <= 5.0
