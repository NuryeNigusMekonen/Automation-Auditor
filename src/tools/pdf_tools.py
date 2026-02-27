from __future__ import annotations

import re
from typing import List, Tuple

from pypdf import PdfReader

from src.state import Evidence


def ingest_pdf_chunks(pdf_path: str, max_chars: int = 2500) -> List[str]:
    reader = PdfReader(pdf_path)
    full: List[str] = []
    for p in reader.pages:
        txt = p.extract_text() or ""
        full.append(txt)
    text = "\n".join(full)

    chunks: List[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + max_chars])
        i += max_chars
    return chunks


def extract_keyword_evidence(
    chunks: List[str], keywords: List[str], goal: str, top_k: int = 3
) -> List[Evidence]:
    joined = "\n".join(chunks)
    low_joined = joined.lower()

    hit_lines: List[str] = []
    found_any = False

    for kw in keywords:
        kw_low = kw.lower()
        if kw_low not in low_joined:
            continue
        found_any = True

        scored: List[Tuple[int, int]] = []
        for i, ch in enumerate(chunks):
            low = (ch or "").lower()
            score = 1 if kw_low in low else 0
            if score > 0:
                scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        for idx, _ in scored[: max(1, top_k)]:
            snippet = (chunks[idx] or "").strip().replace("\n", " ")
            snippet = snippet[:500]
            hit_lines.append(f"keyword={kw} chunk={idx} snippet={snippet}")

    return [
        Evidence(
            goal=goal,
            found=found_any,
            content="\n".join(hit_lines) if hit_lines else None,
            location="pdf",
            rationale="Keyword scan with chunk excerpts",
            confidence=0.75 if found_any else 0.6,
        )
    ]


def extract_report_paths_evidence(chunks: List[str], goal: str) -> List[Evidence]:
    joined = "\n".join(chunks)

    # Handles:
    # - src/foo/bar.py
    # - src\foo\bar.py
    # - paths inside backticks or quotes
    # - paths followed by punctuation
    pat = re.compile(
        r"""(?ix)
        (?:^|[\s"'`(\[])
        
        (
          (?:src|rubric|audit|reports)
          [\\/]
          [A-Za-z0-9_.\-\\/]+
        )
        """
    )

    raw = pat.findall(joined)
    norm: List[str] = []
    for p in raw:
        s = p.strip().strip(".,;:)]}>")
        s = s.replace("\\", "/")
        while "//" in s:
            s = s.replace("//", "/")
        norm.append(s)

    paths = sorted(set(norm))

    return [
        Evidence(
            goal=goal,
            found=bool(paths),
            content="\n".join(paths[:2000]) if paths else None,
            location="pdf",
            rationale="Extracted repo-like paths from PDF text with slash normalization",
            confidence=0.8 if paths else 0.55,
        )
    ]


def query_pdf_evidence(
    chunks: List[str], query: str, goal: str, top_k: int = 3
) -> List[Evidence]:
    q = (query or "").strip().lower()
    if not q:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location="pdf",
                rationale="Empty query",
                confidence=0.8,
            )
        ]

    q_terms = [t for t in re.split(r"[^a-z0-9]+", q) if t]
    if not q_terms:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location="pdf",
                rationale="Query had no usable tokens",
                confidence=0.8,
            )
        ]

    scored: List[Tuple[int, int]] = []
    for i, ch in enumerate(chunks):
        low = (ch or "").lower()
        score = 0
        for t in q_terms:
            if t and t in low:
                score += 1
        if score > 0:
            scored.append((i, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: max(1, top_k)]

    if not top:
        return [
            Evidence(
                goal=goal,
                found=False,
                content=None,
                location="pdf",
                rationale="No matching chunks for query",
                confidence=0.7,
            )
        ]

    content_lines: List[str] = []
    for idx, sc in top:
        snippet = (chunks[idx] or "").strip().replace("\n", " ")
        snippet = snippet[:500]
        content_lines.append(f"chunk={idx} score={sc} snippet={snippet}")

    return [
        Evidence(
            goal=goal,
            found=True,
            content="\n".join(content_lines),
            location="pdf:topk",
            rationale="Chunk retrieval via token overlap scoring",
            confidence=0.75,
        )
    ]
