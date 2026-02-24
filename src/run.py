## Goal
# CLI entry point.

# Checklist
# Parse args: repo, pdf, out, max_concurrency, disable_vision
# Load rubric json from rubric/week2_rubric.json
# Build initial state
# Invoke graph
# Write final_report to output path

## Output
# Running the CLI writes a markdown file under audit/report_onpeer_generated.

# Write report file
# Executive Summary
# Criterion Breakdown
# Remediation Plan

# src/run.py
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from src.graph import build_graph
from src.tools.git_tools import cleanup_workdir


def main() -> int:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="GitHub repo URL")
    ap.add_argument("--pdf", required=True, help="Path to PDF report")
    ap.add_argument("--out", default="audit/report_onpeer_generated/audit_report.md", help="Output markdown path")
    args = ap.parse_args()

    rubric_path = Path("rubric/week2_rubric.json")
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    dims = rubric.get("dimensions", [])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "repo_url": args.repo,
        "pdf_path": args.pdf,
        "out_path": str(out_path),
        "rubric_dimensions": dims,
        "evidences": {},
        "opinions": [],
        "workdir": "",
        "repo_local_path": "",
        "repo_commit_sha": "",
        "final_report": "",
    }

    g = build_graph()
    final_state = None
    try:
        final_state = g.invoke(state)
        out_path.write_text(final_state["final_report"], encoding="utf-8")
        return 0
    finally:
        if final_state and final_state.get("workdir"):
            cleanup_workdir(final_state["workdir"])


if __name__ == "__main__":
    raise SystemExit(main())