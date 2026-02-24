## Goal
# Safe clone and git log extraction.

## Checklist
# Clone into tempfile
# Return commit messages and timestamps
# No os.system
# src/tools/git_tools.py
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class GitCommit:
    sha: str
    ts: str
    msg: str


class GitError(RuntimeError):
    pass


def _run(cmd: List[str], cwd: str | None = None) -> str:
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return p.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Command failed: {' '.join(cmd)}\n{e.stderr.strip()}") from e


def clone_repo(repo_url: str) -> Tuple[str, str]:
    """
    Clones repo into a sandboxed temp directory.
    Returns (repo_path, workdir).
    """
    workdir = tempfile.mkdtemp(prefix="auditor_")
    repo_path = os.path.join(workdir, "repo")
    _run(["git", "clone", "--depth", "50", repo_url, repo_path])
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return repo_path, workdir


def cleanup_workdir(workdir: str) -> None:
    if workdir and os.path.isdir(workdir):
        shutil.rmtree(workdir, ignore_errors=True)


def extract_git_history(repo_path: str) -> List[GitCommit]:
    """
    Uses: git log --oneline --reverse
    Also captures timestamps for narrative.
    """
    # Format: sha|iso-strict|subject
    out = _run(["git", "log", "--reverse", "--pretty=format:%H|%cI|%s"], cwd=repo_path)
    commits: List[GitCommit] = []
    if not out:
        return commits
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        commits.append(GitCommit(sha=parts[0], ts=parts[1], msg=parts[2]))
    return commits


def list_repo_files(repo_path: str) -> List[str]:
    out = _run(["git", "ls-files"], cwd=repo_path)
    return [l.strip() for l in out.splitlines() if l.strip()]


def scan_for_unsafe_os_system(repo_path: str) -> List[str]:
    """
    Heuristic: looks for os.system(...) usage in python files.
    Returns file paths that contain it.
    """
    hits: List[str] = []
    for rel in list_repo_files(repo_path):
        if not rel.endswith(".py"):
            continue
        abs_path = os.path.join(repo_path, rel)
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                txt = f.read()
            if "os.system(" in txt:
                hits.append(rel)
        except OSError:
            continue
    return hits


_PATH_RE = re.compile(r"\b(?:src|rubric|audit)/[A-Za-z0-9_\-./]+\b")


def extract_paths_from_text(text: str) -> List[str]:
    return sorted(set(_PATH_RE.findall(text or "")))