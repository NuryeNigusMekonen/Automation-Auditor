import argparse
import json
import os

from dotenv import load_dotenv

from src.graph import build_graph


def load_rubric(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj["dimensions"]


def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="GitHub repo URL")
    ap.add_argument("--pdf", required=True, help="PDF report path")
    ap.add_argument("--out", required=True, help="Output markdown path")
    ap.add_argument("--rubric", default="rubric/week2_rubric.json", help="Rubric JSON path")
    ap.add_argument("--model", default="gpt-4o-mini", help="LLM model for judges")
    ap.add_argument("--enable-vision", action="store_true", help="Enable PDF image extraction node")
    args = ap.parse_args()

    dims = load_rubric(args.rubric)

    graph = build_graph()

    init_state = {
        "repo_url": args.repo,
        "pdf_path": args.pdf,
        "out_path": args.out,
        "enable_vision": bool(args.enable_vision),
        "model": args.model,
        "rubric_dimensions": dims,
        "workdir": "",
        "repo_local_path": "",
        "repo_commit_sha": "",
        "evidences": {},
        "opinions": [],
        "evidence_packets": {},
        "final_report": None,
    }

    graph.invoke(init_state)
    print(f"Wrote report: {args.out}")


if __name__ == "__main__":
    main()