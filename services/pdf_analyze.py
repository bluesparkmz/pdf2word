"""Detect whether pages are text-based or need OCR."""

from dataclasses import dataclass

import fitz


@dataclass
class PageAnalysis:
    page_index: int
    has_sufficient_text: bool
    char_count: int


def analyze_pdf(pdf_path: str, min_chars: int) -> list[PageAnalysis]:
    doc = fitz.open(pdf_path)
    results: list[PageAnalysis] = []
    try:
        for i in range(len(doc)):
            page = doc[i]
            text = (page.get_text("text") or "").strip()
            count = len(text)
            results.append(
                PageAnalysis(
                    page_index=i,
                    has_sufficient_text=count >= min_chars,
                    char_count=count,
                )
            )
    finally:
        doc.close()
    return results


def pdf_needs_ocr(analyses: list[PageAnalysis]) -> bool:
    if not analyses:
        return True
    ocr_pages = sum(1 for a in analyses if not a.has_sufficient_text)
    return ocr_pages > len(analyses) // 2
