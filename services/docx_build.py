"""Build Word documents from extracted or OCR text."""

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from services.text_extract import TextBlock


def _add_page_break_if_needed(doc: Document, not_first: bool) -> None:
    if not_first:
        doc.add_page_break()


def add_native_page(doc: Document, blocks: list[TextBlock], not_first: bool) -> None:
    _add_page_break_if_needed(doc, not_first)
    if not blocks:
        doc.add_paragraph("(página sem texto legível)")
        return
    sizes = [b.size for b in blocks if b.size > 0]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 12.0
    for block in blocks:
        p = doc.add_paragraph()
        run = p.add_run(block.text)
        if block.is_bold:
            run.bold = True
        if block.size >= body_size * 1.35:
            run.font.size = Pt(min(block.size, 28))
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            run.font.size = Pt(11)


def add_ocr_page(doc: Document, text: str, page_num: int, not_first: bool) -> None:
    _add_page_break_if_needed(doc, not_first)
    heading = doc.add_paragraph(f"Página {page_num + 1} (OCR)")
    if heading.runs:
        heading.runs[0].italic = True
        heading.runs[0].font.size = Pt(9)
    body = text.strip() if text else "(sem texto reconhecido)"
    for para in body.split("\n\n"):
        para = para.strip()
        if para:
            doc.add_paragraph(para)


def new_document(title: str) -> Document:
    doc = Document()
    doc.core_properties.title = title
    doc.add_heading(title, level=0)
    return doc
