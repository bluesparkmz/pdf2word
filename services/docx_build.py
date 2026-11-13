"""Build Word documents from extracted or OCR text."""

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Mm, Pt

from services.page_content import PageElement, ParagraphElement, TableElement
from services.table_spans import SpanCellInfo
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


def _add_paragraph_block(doc: Document, block: TextBlock, body_size: float) -> None:
    p = doc.add_paragraph()
    run = p.add_run(block.text)
    if block.is_bold:
        run.bold = True
    if block.size >= body_size * 1.35:
        run.font.size = Pt(min(block.size, 28))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        run.font.size = Pt(11)


def _style_cell(cell, text: str, *, header: bool = False) -> None:
    cell.text = text
    for para in cell.paragraphs:
        for run in para.runs:
            run.font.size = Pt(10)
            if header:
                run.bold = True


def _add_word_table_spans(doc: Document, span_rows: list[list[SpanCellInfo]]) -> None:
    col_count = max(sum(c.colspan for c in row) for row in span_rows)
    row_count = len(span_rows)
    table = doc.add_table(rows=row_count, cols=col_count)
    try:
        table.style = "Table Grid"
    except KeyError:
        pass

    occupied = [[False] * col_count for _ in range(row_count)]

    for ri, row_cells in enumerate(span_rows):
        ci = 0
        for cell_info in row_cells:
            while ci < col_count and occupied[ri][ci]:
                ci += 1
            if ci >= col_count:
                break
            end_ri = min(row_count - 1, ri + cell_info.rowspan - 1)
            end_ci = min(col_count - 1, ci + cell_info.colspan - 1)
            origin = table.cell(ri, ci)
            if cell_info.rowspan > 1 or cell_info.colspan > 1:
                origin.merge(table.cell(end_ri, end_ci))
            _style_cell(origin, cell_info.text, header=cell_info.tag == "th")
            for rr in range(ri, end_ri + 1):
                for cc in range(ci, end_ci + 1):
                    occupied[rr][cc] = True
            ci += cell_info.colspan
    doc.add_paragraph()


def _add_word_table(doc: Document, rows: list[list[str]]) -> None:
    col_count = max(len(row) for row in rows)
    row_count = len(rows)
    table = doc.add_table(rows=row_count, cols=col_count)
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
    for ri, row in enumerate(rows):
        for ci in range(col_count):
            text = row[ci] if ci < len(row) else ""
            _style_cell(table.rows[ri].cells[ci], text)
    doc.add_paragraph()


def _add_table_element(doc: Document, element: TableElement) -> None:
    if element.span_rows:
        _add_word_table_spans(doc, element.span_rows)
    else:
        _add_word_table(doc, element.rows)


def add_page_elements(doc: Document, elements: list[PageElement]) -> None:
    if not elements:
        doc.add_paragraph("(página sem texto legível)")
        return
    para_blocks = [e.block for e in elements if isinstance(e, ParagraphElement)]
    sizes = [b.size for b in para_blocks if b.size > 0]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 12.0
    for el in elements:
        if isinstance(el, TableElement):
            _add_table_element(doc, el)
        else:
            _add_paragraph_block(doc, el.block, body_size)


def add_native_page(doc: Document, blocks: list[TextBlock]) -> None:
    """Legacy: paragraphs only."""
    add_page_elements(
        doc,
        [ParagraphElement(y0=0.0, block=b) for b in blocks],
    )


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
