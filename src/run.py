from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from src.graph import build_graph


def load_rubric_dimensions(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    dims = obj.get("dimensions", [])
    if not isinstance(dims, list):
        raise ValueError("rubric.dimensions must be a list")
    return dims


def main() -> None:
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rubric", default="rubric/week2_rubric.json")
    ap.add_argument("--enable-vision", action="store_true")
    args = ap.parse_args()

    rubric_dimensions = load_rubric_dimensions(args.rubric)

    init_state = {
        "repo_url": args.repo,
        "pdf_path": args.pdf,
        "rubric_dimensions": rubric_dimensions,
        "enable_vision": bool(args.enable_vision),
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "final_report_markdown": "",
    }

    graph = build_graph()
    out_state = graph.invoke(init_state)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md = out_state.get("final_report_markdown") or ""
    if not md:
        fr = out_state.get("final_report")
        md = fr.model_dump_json(indent=2) if fr is not None else ""

    out_path.write_text(md or "No report generated.", encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()