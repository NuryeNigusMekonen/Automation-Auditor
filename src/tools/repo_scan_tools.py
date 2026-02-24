from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from src.state import Evidence


def _read_text(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1", errors="ignore")
    except Exception:
        return None


def scan_state_management(repo_path: str) -> List[Evidence]:
    goal = "state_management_rigor"
    root = Path(repo_path)

    candidates = [
        root / "src" / "state.py",
        root / "state.py",
    ]
    state_file = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not state_file:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location="repo",
                rationale="No state.py found in common locations",
                confidence=0.95,
            )
        ]

    txt = _read_text(state_file) or ""
    has_pydantic = "from pydantic" in txt or "BaseModel" in txt
    has_typeddict = "TypedDict" in txt
    has_annotated = "Annotated" in txt
    has_reducers = "operator.add" in txt or "operator.ior" in txt

    content = "\n".join(
        [
            f"state_file={state_file}",
            f"has_pydantic={has_pydantic}",
            f"has_typeddict={has_typeddict}",
            f"has_annotated={has_annotated}",
            f"has_reducers={has_reducers}",
        ]
    )

    found = has_pydantic or has_typeddict
    return [
        Evidence(
            goal=goal,
            found=found,
            content=content,
            location=str(state_file),
            rationale="File scan for typed state and reducers",
            confidence=0.85,
        )
    ]


def scan_safe_tooling(repo_path: str) -> List[Evidence]:
    goal = "safe_tool_engineering"
    root = Path(repo_path)

    py_files = []
    for p in root.rglob("*.py"):
        sp = str(p)
        if "/.venv/" in sp or "/venv/" in sp or "__pycache__" in sp:
            continue
        py_files.append(p)

    os_system_hits: List[str] = []
    tmpdir_hits: List[str] = []
    subprocess_hits: List[str] = []

    for p in py_files[:5000]:
        txt = _read_text(p)
        if not txt:
            continue
        if "os.system(" in txt:
            os_system_hits.append(str(p))
        if "tempfile.TemporaryDirectory" in txt:
            tmpdir_hits.append(str(p))
        if "subprocess.run(" in txt:
            subprocess_hits.append(str(p))

    found_safe_signals = bool(tmpdir_hits) and bool(subprocess_hits) and not bool(os_system_hits)

    content = "\n".join(
        [
            f"os_system_files={os_system_hits[:20]}",
            f"tempdir_files={tmpdir_hits[:20]}",
            f"subprocess_files={subprocess_hits[:20]}",
        ]
    )

    rationale = "Repo-wide scan for os.system usage and sandbox signals"
    if os_system_hits:
        rationale = "Found os.system usage. Unsafe by rubric."

    loc = "repo_scan"
    if os_system_hits:
        loc = os_system_hits[0]
    elif tmpdir_hits:
        loc = tmpdir_hits[0]
    elif subprocess_hits:
        loc = subprocess_hits[0]

    return [
        Evidence(
            goal=goal,
            found=found_safe_signals,
            content=content or None,
            location=loc,
            rationale=rationale,
            confidence=0.8,
        )
    ]