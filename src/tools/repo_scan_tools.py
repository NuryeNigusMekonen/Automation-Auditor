# src/tools/repo_scan_tools.py
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional, Tuple

from src.state import Evidence


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _attr_chain(node: ast.AST) -> Optional[Tuple[str, ...]]:
    parts: List[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return tuple(reversed(parts))
    return None


def scan_for_os_system(repo_path: str) -> List[Evidence]:
    root = Path(repo_path)
    tools_dir = root / "src" / "tools"

    if not tools_dir.exists():
        return [
            Evidence(
                goal="safe_tool_engineering",
                found=False,
                content="src/tools not found",
                location="src/tools",
                rationale="Tools directory missing",
                confidence=0.9,
            )
        ]

    unsafe_hits: List[str] = []
    safe_signals: List[str] = []
    parse_errors: List[str] = []

    for p in tools_dir.rglob("*.py"):
        sp = str(p)
        if "/.venv/" in sp or "/venv/" in sp or "__pycache__" in sp:
            continue

        txt = _read_text(p)
        rel = p.relative_to(root).as_posix()

        try:
            tree = ast.parse(txt)
        except SyntaxError as e:
            # Parse errors are not security flaws. Record separately.
            parse_errors.append(f"{rel}:{getattr(e, 'lineno', 1)}: SyntaxError: {e}")
            continue

        class V(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                chain = _attr_chain(node.func)

                if chain == ("os", "system"):
                    unsafe_hits.append(
                        f"{rel}:{getattr(node, 'lineno', 0)}: os.system(...)"
                    )

                if (
                    chain
                    and chain[0] == "subprocess"
                    and chain[1:]
                    in {
                        ("run",),
                        ("Popen",),
                        ("call",),
                        ("check_call",),
                        ("check_output",),
                    }
                ):
                    shell_kw = None
                    for kw in node.keywords or []:
                        if kw.arg == "shell":
                            shell_kw = kw.value
                            break

                    if (
                        shell_kw is not None
                        and isinstance(shell_kw, ast.Constant)
                        and shell_kw.value is True
                    ):
                        unsafe_hits.append(
                            f"{rel}:{getattr(node, 'lineno', 0)}: subprocess.{chain[-1]}(shell=True)"
                        )

                if chain == ("tempfile", "TemporaryDirectory"):
                    safe_signals.append(
                        f"{rel}:{getattr(node, 'lineno', 0)}: tempfile.TemporaryDirectory"
                    )

                if chain == ("subprocess", "run"):
                    shell_true = False
                    for kw in node.keywords or []:
                        if (
                            kw.arg == "shell"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True
                        ):
                            shell_true = True
                            break
                    if not shell_true:
                        safe_signals.append(
                            f"{rel}:{getattr(node, 'lineno', 0)}: subprocess.run(no shell)"
                        )

                self.generic_visit(node)

        V().visit(tree)

    ok = len(unsafe_hits) == 0

    lines: List[str] = []

    if unsafe_hits:
        lines.append("Unsafe execution call sites detected:")
        lines.extend(sorted(set(unsafe_hits))[:500])
    else:
        lines.append("No unsafe execution call sites detected by AST scan.")

    if parse_errors:
        lines.append("Parse errors (not counted as security flaws):")
        lines.extend(sorted(set(parse_errors))[:200])

    if safe_signals:
        lines.append("Safe signals detected:")
        lines.extend(sorted(set(safe_signals))[:500])

    confidence = 0.95 if ok else 0.9
    if parse_errors and ok:
        # Slightly reduce confidence if we could not scan some files.
        confidence = min(confidence, 0.9)

    return [
        Evidence(
            goal="safe_tool_engineering",
            found=ok,
            content="\n".join(lines),
            location="src/tools",
            rationale="AST scan for os.system and subprocess shell=True. Parse errors recorded separately to avoid false security flags.",
            confidence=confidence,
        )
    ]
