# src/tools/pdf_tools.py
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


def extract_keyword_evidence(chunks: List[str], keywords: List[str], goal: str) -> List[Evidence]:
    joined = "\n".join(chunks)
    low = joined.lower()

    hits: List[str] = []
    for k in keywords:
        if k.lower() in low:
            hits.append(k)

    return [
        Evidence(
            goal=goal,
            found=bool(hits),
            content=("Keywords found: " + ", ".join(hits)) if hits else None,
            location="pdf",
            rationale="Keyword scan over extracted PDF text",
            confidence=0.7 if hits else 0.6,
        )
    ]


def extract_report_paths_evidence(chunks: List[str], goal: str) -> List[Evidence]:
    joined = "\n".join(chunks)
    paths = sorted(set(re.findall(r"\b(?:src|rubric|audit|reports)/[A-Za-z0-9_./-]+\b", joined)))

    return [
        Evidence(
            goal=goal,
            found=bool(paths),
            content="\n".join(paths[:200]) if paths else None,
            location="pdf",
            rationale="Regex extraction of repo-like paths from PDF text",
            confidence=0.65 if paths else 0.55,
        )
    ]


def query_pdf_evidence(chunks: List[str], query: str, goal: str, top_k: int = 3) -> List[Evidence]:
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
        snippet = chunks[idx].strip().replace("\n", " ")
        snippet = snippet[:500]
        content_lines.append(f"chunk={idx} score={sc} snippet={snippet}")

    return [
        Evidence(
            goal=goal,
            found=True,
            content="\n".join(content_lines),
            location="pdf:topk",
            rationale="RAG-lite chunk retrieval using token overlap scoring",
            confidence=0.75,
        )
    ]