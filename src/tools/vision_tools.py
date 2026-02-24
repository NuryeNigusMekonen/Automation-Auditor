from __future__ import annotations

from typing import List

from pypdf import PdfReader

from src.state import Evidence


def analyze_pdf_diagrams_safe(pdf_path: str) -> List[Evidence]:
    """
    Safe default.
    Extracts page count. Does not call any vision model.
    You can replace later with real image extraction + multimodal LLM.
    """
    try:
        r = PdfReader(pdf_path)
        n_pages = len(r.pages)
        return [
            Evidence(
                goal="swarm_visual",
                found=False,
                content=f"Vision enabled, but not implemented. pdf_pages={n_pages}",
                location="pdf_images",
                rationale="Vision stub. No image extraction yet.",
                confidence=1.0,
            )
        ]
    except Exception as e:
        return [
            Evidence(
                goal="swarm_visual",
                found=False,
                content=f"Vision stub failed: {e}",
                location="pdf_images",
                rationale="Could not read PDF for page count",
                confidence=0.8,
            )
        ]