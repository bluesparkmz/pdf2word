"""Build Word documents from extracted or OCR text."""

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Mm, Pt

from services.text_extract import TextBlock

# PDF page sizes in points (1/72 inch); snap when close for exact paper in Word
_PAPER_MM: list[tuple[tuple[float, float], tuple[float, float]]] = [
    ((595.276, 841.890), (210.0, 297.0)),  # A4 portrait
    ((841.890, 595.276), (297.0, 210.0)),  # A4 landscape
    ((612.0, 792.0), (215.9, 279.4)),  # Letter
    ((792.0, 612.0), (279.4, 215.9)),  # Letter landscape
    ((522.0, 756.0), (184.2, 266.7)),  # B5
]


def _snap_paper_mm(width_pt: float, height_pt: float) -> tuple[float, float] | None:
    for (pw, ph), (mw, mh) in _PAPER_MM:
        if abs(width_pt - pw) < 2.5 and abs(height_pt - ph) < 2.5:
            return mw, mh
    return None


def apply_page_size(section, width_pt: float, height_pt: float) -> None:
    """Match Word section dimensions to the PDF page (points)."""
    portrait = height_pt >= width_pt
    snapped = _snap_paper_mm(width_pt, height_pt)
    if snapped:
        mw, mh = snapped
        section.orientation = WD_ORIENT.PORTRAIT if portrait else WD_ORIENT.LANDSCAPE
        if portrait:
            section.page_width = Mm(mw)
            section.page_height = Mm(mh)
        else:
            section.page_width = Mm(max(mw, mh))
            section.page_height = Mm(min(mw, mh))
        return

    w_in = width_pt / 72.0
    h_in = height_pt / 72.0
    if portrait:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Inches(w_in)
        section.page_height = Inches(h_in)
    else:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(max(w_in, h_in))
        section.page_height = Inches(min(w_in, h_in))


def apply_document_page_size(doc: Document, width_pt: float, height_pt: float) -> None:
    apply_page_size(doc.sections[0], width_pt, height_pt)


def page_size_key(width_pt: float, height_pt: float) -> tuple[float, float]:
    return (round(width_pt, 1), round(height_pt, 1))


def start_new_page(doc: Document, width_pt: float, height_pt: float, *, new_size: bool) -> None:
    if new_size:
        section = doc.add_section()
        apply_page_size(section, width_pt, height_pt)
    else:
        doc.add_page_break()


def add_native_page(doc: Document, blocks: list[TextBlock]) -> None:
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


def add_ocr_page(doc: Document, text: str, page_num: int) -> None:
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
    return doc
