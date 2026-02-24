import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GitCommit:
    sha: str
    ts: str
    msg: str


class GitToolError(RuntimeError):
    pass


def _run(cmd: List[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as e:
        raise GitToolError(f"Command failed to start: {cmd}. Error: {e}") from e


def clone_repo(repo_url: str) -> Tuple[str, str]:
    """
    Clones into an isolated temp directory.
    Returns (workdir, repo_path).
    """
    workdir = tempfile.mkdtemp(prefix="auditor_repo_")
    repo_path = os.path.join(workdir, "repo")

    cp = _run(["git", "clone", "--depth", "200", repo_url, repo_path])
    if cp.returncode != 0:
        shutil.rmtree(workdir, ignore_errors=True)
        raise GitToolError(f"git clone failed: {cp.stderr.strip()}")

    return workdir, repo_path


def get_head_commit(repo_path: str) -> str:
    cp = _run(["git", "rev-parse", "HEAD"], cwd=repo_path)
    if cp.returncode != 0:
        raise GitToolError(f"git rev-parse failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def get_git_log(repo_path: str, max_commits: int = 200) -> List[GitCommit]:
    fmt = "%H|%ct|%s"
    cp = _run(["git", "log", f"--max-count={max_commits}", f"--pretty=format:{fmt}", "--reverse"], cwd=repo_path)
    if cp.returncode != 0:
        raise GitToolError(f"git log failed: {cp.stderr.strip()}")

    commits: List[GitCommit] = []
    for line in cp.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        commits.append(GitCommit(sha=parts[0], ts=parts[1], msg=parts[2]))
    return commits


def list_repo_files(repo_path: str) -> List[str]:
    out: List[str] = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, repo_path)
            out.append(rel)
    return sorted(out)


def scan_for_os_system(repo_path: str) -> bool:
    """
    Quick security check.
    This is NOT used as the main analysis for structure, only as a security signal.
    """
    for rel in list_repo_files(repo_path):
        if not rel.endswith(".py"):
            continue
        abs_p = os.path.join(repo_path, rel)
        try:
            with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            if "os.system(" in txt:
                return True
        except Exception:
            continue
    return False