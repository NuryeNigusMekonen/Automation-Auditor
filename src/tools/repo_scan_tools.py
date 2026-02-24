# src/tools/repo_scan_tools.py
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from src.state import Evidence


def _run(cmd: List[str], cwd: str | None = None) -> Tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def clone_repo_sandboxed(repo_url: str) -> str:
    tmpdir = tempfile.TemporaryDirectory(prefix="auditor_repo_")
    repo_path = Path(tmpdir.name) / "repo"

    code, out, err = _run(["git", "clone", "--depth", "200", repo_url, str(repo_path)])
    if code != 0:
        tmpdir.cleanup()
        raise RuntimeError(f"git clone failed. stdout={out.strip()} stderr={err.strip()}")

    if not hasattr(clone_repo_sandboxed, "_keepers"):
        clone_repo_sandboxed._keepers = []  # type: ignore[attr-defined]
    clone_repo_sandboxed._keepers.append(tmpdir)  # type: ignore[attr-defined]

    return str(repo_path)


def extract_git_history(repo_path: str) -> List[Evidence]:
    code, out, err = _run(["git", "-C", repo_path, "log", "--oneline", "--reverse", "--date=iso-strict"])
    found = code == 0 and out.strip() != ""
    content = out.strip() if found else (err.strip() or None)

    return [
        Evidence(
            goal="git_forensic_analysis",
            found=found,
            content=content,
            location="git log",
            rationale="Collected git log from cloned repo in sandbox temp directory",
            confidence=0.9 if found else 0.6,
        )
    ]


def scan_for_os_system(repo_path: str) -> List[Evidence]:
    root = Path(repo_path)
    tools_dir = root / "src" / "tools"

    hits = []
    safe_signals = []

    for p in tools_dir.rglob("*.py"):
        s = str(p)
        if any(x in s for x in ["/.venv/", "/venv/", "__pycache__"]):
            continue

        txt = p.read_text(encoding="utf-8", errors="ignore")

        if "os.system(" in txt:
            hits.append(str(p))

        if "subprocess.run(" in txt:
            safe_signals.append(f"{p}: uses subprocess.run")

        if "TemporaryDirectory(" in txt:
            safe_signals.append(f"{p}: uses TemporaryDirectory")

    found = False if hits else True

    content_lines = []
    if hits:
        content_lines.append("Unsafe usage detected:")
        content_lines.extend(hits)
    else:
        content_lines.append("No os.system usage detected.")

    if safe_signals:
        content_lines.append("Safe signals detected:")
        content_lines.extend(safe_signals)

    return [
        Evidence(
            goal="safe_tool_engineering",
            found=found,
            content="\n".join(content_lines),
            location="src/tools",
            rationale="Static scan for unsafe shell execution and safe subprocess usage",
            confidence=0.95 if found else 0.8,
        )
    ]

def scan_for_repo_url_in_shell(repo_path: str) -> List[Evidence]:
    root = Path(repo_path)
    hits: List[str] = []
    pattern = re.compile(r"os\.system\(|subprocess\.(run|Popen)\(", re.IGNORECASE)

    for p in root.rglob("*.py"):
        s = str(p)
        if "/.venv/" in s or "/venv/" in s or "__pycache__" in s:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pattern.search(txt):
            hits.append(str(p))

    return [
        Evidence(
            goal="safe_tool_engineering",
            found=True,
            content=("Shell execution call sites:\n" + "\n".join(hits[:200])) if hits else "No shell execution call sites detected.",
            location="repo scan",
            rationale="Locate command execution surfaces for review",
            confidence=0.7,
        )
    ]
