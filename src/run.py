from __future__ import annotations

import argparse
import json
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.config import RuntimeConfig, load_rubric_dimensions
from src.graph import build_graph


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit_log(message: str, log_file_path: str | None = None) -> None:
    line = f"[{_timestamp_utc()}] {message}"
    print(line)
    if not log_file_path:
        return
    p = Path(log_file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    load_dotenv()
    warnings.filterwarnings(
        "ignore",
        message=r"Pydantic serializer warnings:.*field_name='parsed'.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module=r"pydantic\.main",
    )

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rubric", default="rubric/week2_rubric.json")

    # Enhanced argument parsing for vision flags
    ap.add_argument("--enable-vision", action="store_true", help="Enable PDF diagram inspection")
    ap.add_argument("--disable-vision", action="store_true", help="Disable PDF diagram inspection")
    ap.add_argument("--offline", action="store_true", help="Disable LLM calls and run deterministic offline judge mode")
    ap.add_argument("--verbose", action="store_true", help="Print step-by-step node execution logs")
    ap.add_argument("--log-file", help="Path to save timestamped execution logs")
    args = ap.parse_args()

    if args.enable_vision and args.disable_vision:
        raise SystemExit("Pick only one: --enable-vision or --disable-vision")

    enable_vision = True if args.enable_vision else False
    if args.disable_vision:
        enable_vision = False

    log_file_path = args.log_file
    if args.verbose and not log_file_path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_file_path = str(Path("audit") / "logs" / f"run_{ts}.log")

    runtime_config = RuntimeConfig.from_sources(
        enable_vision=enable_vision,
        offline_mode=bool(args.offline),
        verbose_logging=bool(args.verbose),
        log_file_path=log_file_path,
    )

    rubric_dimensions = load_rubric_dimensions(args.rubric)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="auditor_run_") as workdir:
        init_state = {
            "repo_url": args.repo,
            "pdf_path": args.pdf,
            "rubric_dimensions": rubric_dimensions,
            "enable_vision": runtime_config.enable_vision,
            "offline_mode": runtime_config.offline_mode,
            "runtime_config": runtime_config.model_dump(),
            "workspace_dir": workdir,
            "evidences": {},
            "opinions": [],
            "final_report": None,
            "final_report_markdown": "",
        }

        if runtime_config.verbose_logging:
            _emit_log(
                "[RUN] Starting pipeline "
                f"repo={args.repo} pdf={args.pdf} "
                f"vision={runtime_config.enable_vision} offline={runtime_config.offline_mode}",
                runtime_config.log_file_path,
            )
            if runtime_config.log_file_path:
                _emit_log(
                    f"[RUN] Logging to {runtime_config.log_file_path}",
                    runtime_config.log_file_path,
                )

        graph = build_graph()
        out_state = graph.invoke(init_state)

    md = out_state.get("final_report_markdown") or ""

    if not md:
        fr = out_state.get("final_report")
        if fr is not None:
            if hasattr(fr, "model_dump"):
                fr = fr.model_dump()
            md = json.dumps(fr, indent=2, ensure_ascii=False, default=str)

    out_path.write_text(md or "No report generated.", encoding="utf-8")
    if runtime_config.verbose_logging:
        _emit_log(f"[RUN] Wrote report: {out_path}", runtime_config.log_file_path)
    else:
        print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()