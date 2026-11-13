"""Orchestrate PDF → DOCX with hybrid native text + OCR."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pymupdf as fitz

from config import settings
from services.docx_build import (
    add_native_page,
    add_ocr_page,
    apply_document_page_size,
    new_document,
    page_size_key,
    start_new_page,
)
from services.ocr import ocr_pdf_pages
from services.pdf_analyze import analyze_pdf, pdf_needs_ocr
from services.text_extract import extract_page_blocks


class OcrMode(str, Enum):
    AUTO = "auto"
    FORCE = "force"
    OFF = "off"


@dataclass
class ConversionResult:
    output_path: Path
    pages: int
    ocr_pages: int
    native_pages: int
    mode_used: str


def convert_pdf_to_docx(
    pdf_path: Path,
    output_path: Path,
    *,
    ocr_mode: OcrMode = OcrMode.AUTO,
    ocr_lang: str | None = None,
    dpi: int | None = None,
) -> ConversionResult:
    lang = ocr_lang or settings.default_ocr_lang
    resolution = dpi or settings.ocr_dpi
    analyses = analyze_pdf(str(pdf_path), settings.min_text_chars_per_page)
    page_count = len(analyses)

    use_ocr_globally = ocr_mode == OcrMode.FORCE
    use_ocr_auto = ocr_mode == OcrMode.AUTO and pdf_needs_ocr(analyses)
    hybrid = ocr_mode == OcrMode.AUTO and not use_ocr_auto and not use_ocr_globally

    ocr_indices: list[int] = []
    if use_ocr_globally or use_ocr_auto:
        ocr_indices = list(range(page_count))
    elif hybrid:
        ocr_indices = [a.page_index for a in analyses if not a.has_sufficient_text]

    ocr_text: dict[int, str] = {}
    if ocr_indices and ocr_mode != OcrMode.OFF:
        ocr_text = ocr_pdf_pages(str(pdf_path), ocr_indices, lang, resolution)

    doc = new_document(pdf_path.stem)
    native_count = 0
    ocr_count = 0

    pdf = fitz.open(str(pdf_path))
    try:
        last_size: tuple[float, float] | None = None
        for i in range(page_count):
            page = pdf[i]
            rect = page.rect
            size = page_size_key(rect.width, rect.height)
            if i == 0:
                apply_document_page_size(doc, rect.width, rect.height)
            elif last_size is not None and size != last_size:
                start_new_page(doc, rect.width, rect.height, new_size=True)
            elif i > 0:
                start_new_page(doc, rect.width, rect.height, new_size=False)
            last_size = size

            needs_ocr_page = ocr_mode != OcrMode.OFF and (
                use_ocr_globally or use_ocr_auto or i in ocr_indices
            )
            if needs_ocr_page:
                add_ocr_page(doc, ocr_text.get(i, ""), i)
                ocr_count += 1
            else:
                blocks = extract_page_blocks(page)
                add_native_page(doc, blocks)
                native_count += 1
    finally:
        pdf.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))

    if use_ocr_globally:
        mode = "force_ocr"
    elif hybrid and ocr_count:
        mode = "hybrid"
    elif use_ocr_auto:
        mode = "auto_ocr"
    else:
        mode = "native"

    return ConversionResult(
        output_path=output_path,
        pages=page_count,
        ocr_pages=ocr_count,
        native_pages=native_count,
        mode_used=mode,
    )
