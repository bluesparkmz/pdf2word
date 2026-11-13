"""Ordered page content: paragraphs and tables (PyMuPDF find_tables)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import pymupdf as fitz

from services.pdf_images import PdfImage, extract_page_images
from services.table_layout import column_widths_pt
from services.table_spans import SpanCellInfo, flat_rows_from_table, flat_rows_with_styles, span_rows_from_table
from services.text_extract import TextBlock, text_block_from_bbox


@dataclass
class ImageElement:
    y0: float
    image: PdfImage


@dataclass
class TableElement:
    y0: float
    rows: list[list[str]]
    span_rows: list[list[SpanCellInfo]] | None = None
    col_widths_pt: list[float] | None = None


@dataclass
class ParagraphElement:
    y0: float
    block: TextBlock


PageElement = Union[TableElement, ParagraphElement, ImageElement]


def _rect_from_bbox(bbox) -> fitz.Rect:
    if isinstance(bbox, fitz.Rect):
        return bbox
    return fitz.Rect(bbox)


def _center_in_table(cx: float, cy: float, table_rects: list[fitz.Rect]) -> bool:
    for rect in table_rects:
        if rect.contains((cx, cy)):
            return True
    return False


def extract_page_content(page: fitz.Page) -> list[PageElement]:
    elements: list[PageElement] = []
    table_rects: list[fitz.Rect] = []

    try:
        found = page.find_tables(refine=True)
        for table in found.tables:
            span_rows = span_rows_from_table(page, table)
            rows = flat_rows_from_table(table)
            if not span_rows:
                span_rows = flat_rows_with_styles(page, table)
            if span_rows:
                has_text = any(cell.text for row in span_rows for cell in row)
            else:
                has_text = any(any(c for c in row) for row in rows)
            if not has_text:
                continue
            rect = _rect_from_bbox(table.bbox)
            table_rects.append(rect)
            col_w = column_widths_pt(table)
            elements.append(
                TableElement(
                    y0=rect.y0,
                    rows=rows,
                    span_rows=span_rows,
                    col_widths_pt=col_w or None,
                ),
            )
    except Exception:
        pass

    data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox")
        if not bbox:
            continue
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        if table_rects and _center_in_table(cx, cy, table_rects):
            continue
        tb = text_block_from_bbox(page, bbox)
        if tb:
            elements.append(ParagraphElement(y0=bbox[1], block=tb))

    for img in extract_page_images(page, table_rects):
        elements.append(ImageElement(y0=img.y0, image=img))

    if not elements:
        plain = (page.get_text("text") or "").strip()
        if plain:
            elements.append(ParagraphElement(y0=0.0, block=TextBlock(text=plain, size=12.0, is_bold=False)))

    elements.sort(key=lambda e: e.y0)
    return elements
