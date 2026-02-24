from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from src.state import Evidence


def clone_repo_sandboxed(repo_url: str) -> str:
    tmpdir = tempfile.TemporaryDirectory(prefix="auditor_repo_")
    repo_path = Path(tmpdir.name) / "repo"

    proc = subprocess.run(
        ["git", "clone", "--depth", "200", repo_url, str(repo_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        tmpdir.cleanup()
        raise RuntimeError(f"git clone failed. stdout={stdout} stderr={stderr}")

    if not hasattr(clone_repo_sandboxed, "_keepers"):
        clone_repo_sandboxed._keepers = []  # type: ignore[attr-defined]
    clone_repo_sandboxed._keepers.append(tmpdir)  # type: ignore[attr-defined]

    return str(repo_path)


def _git(repo_path: str, args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", repo_path] + args,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def extract_git_history(repo_path: str) -> List[Evidence]:
    code, out, err = _git(
        repo_path,
        ["log", "--reverse", "--date=iso-strict", "--pretty=format:%H %ad %s"],
    )
    found = code == 0 and out.strip() != ""

    content = out.strip() if found else ((err.strip() or None))

    return [
        Evidence(
            goal="git_forensic_analysis",
            found=found,
            content=content,
            location="git log",
            rationale="Collected git log with hashes and iso timestamps",
            confidence=0.95 if found else 0.6,
        )
    ]