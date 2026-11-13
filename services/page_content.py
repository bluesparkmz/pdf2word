"""Ordered page content: paragraphs and tables (PyMuPDF find_tables)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import pymupdf as fitz

from services.text_extract import TextBlock


@dataclass
class TableElement:
    y0: float
    rows: list[list[str]]


@dataclass
class ParagraphElement:
    y0: float
    block: TextBlock


PageElement = Union[TableElement, ParagraphElement]


def _rect_from_bbox(bbox) -> fitz.Rect:
    if isinstance(bbox, fitz.Rect):
        return bbox
    return fitz.Rect(bbox)


def _center_in_table(cx: float, cy: float, table_rects: list[fitz.Rect]) -> bool:
    for rect in table_rects:
        if rect.contains((cx, cy)):
            return True
    return False


def _text_block_from_dict(block: dict) -> TextBlock | None:
    lines_text: list[str] = []
    max_size = 0.0
    bold = False
    for line in block.get("lines", []):
        line_parts: list[str] = []
        for span in line.get("spans", []):
            t = span.get("text", "")
            if not t:
                continue
            size = float(span.get("size", 12))
            max_size = max(max_size, size)
            if int(span.get("flags", 0)) & 16:
                bold = True
            line_parts.append(t)
        if line_parts:
            lines_text.append("".join(line_parts))
    joined = "\n".join(lines_text).strip()
    if not joined:
        return None
    return TextBlock(text=joined, size=max_size or 12.0, is_bold=bold)


def extract_page_content(page: fitz.Page) -> list[PageElement]:
    elements: list[PageElement] = []
    table_rects: list[fitz.Rect] = []

    try:
        found = page.find_tables()
        for table in found.tables:
            raw = table.extract()
            if not raw:
                continue
            rows = [[(cell or "").strip() for cell in row] for row in raw]
            if not any(any(c for c in row) for c in rows):
                continue
            rect = _rect_from_bbox(table.bbox)
            table_rects.append(rect)
            elements.append(TableElement(y0=rect.y0, rows=rows))
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
        tb = _text_block_from_dict(block)
        if tb:
            elements.append(ParagraphElement(y0=bbox[1], block=tb))

    if not elements:
        plain = (page.get_text("text") or "").strip()
        if plain:
            elements.append(ParagraphElement(y0=0.0, block=TextBlock(text=plain, size=12.0, is_bold=False)))

    elements.sort(key=lambda e: e.y0)
    return elements
