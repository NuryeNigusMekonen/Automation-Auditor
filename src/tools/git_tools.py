# src/tools/git_tools.py
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from src.state import Evidence


def _classify_git_clone_error(stderr: str, stdout: str) -> str:
    s = (stderr or "") + "\n" + (stdout or "")
    low = s.lower()

    if "authentication failed" in low or "could not read username" in low or "permission denied" in low:
        return "auth_failed"
    if "repository not found" in low or "not found" in low:
        return "repo_not_found"
    if "rate limit" in low or "too many requests" in low:
        return "rate_limited"
    if "could not resolve host" in low or "name or service not known" in low:
        return "dns_failed"
    if "failed to connect" in low or "connection timed out" in low:
        return "network_failed"
    return "unknown"


def validate_repo_url(repo_url: str) -> None:
    if not repo_url or len(repo_url) > 300:
        raise ValueError("Invalid repo URL length")

    if re.search(r"[ \t\n\r;|&`$<>]", repo_url):
        raise ValueError("Repo URL contains unsafe characters")

    u = urlparse(repo_url)
    if u.scheme != "https":
        raise ValueError("Repo URL must use https")
    if u.netloc not in {"github.com"}:
        raise ValueError("Only github.com is allowed")
    if not u.path or u.path.count("/") < 2:
        raise ValueError("Repo URL must look like https://github.com/owner/repo")


def clone_repo_sandboxed(repo_url: str) -> str:
    validate_repo_url(repo_url)

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
        code = _classify_git_clone_error(stderr, stdout)
        tmpdir.cleanup()
        raise RuntimeError(f"git clone failed ({code}). stdout={stdout} stderr={stderr}")

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