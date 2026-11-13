"""Extract text and layout hints from native PDF text layers."""

from dataclasses import dataclass, field

import pymupdf as fitz

from services.pdf_style import TextRun, dominant_run_style, runs_to_plain, styled_runs_in_rect


@dataclass
class TextBlock:
    text: str
    size: float
    is_bold: bool
    runs: list[TextRun] = field(default_factory=list)
    color_rgb: tuple[int, int, int] | None = None


def text_block_from_bbox(page: fitz.Page, bbox: tuple | fitz.Rect) -> TextBlock | None:
    rect = fitz.Rect(bbox)
    runs = styled_runs_in_rect(page, rect)
    if not runs:
        return None
    plain = runs_to_plain(runs)
    if not plain:
        return None
    bold, color, size = dominant_run_style(runs)
    return TextBlock(text=plain, size=size, is_bold=bold, runs=runs, color_rgb=color)


def extract_page_blocks(page: fitz.Page) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox")
        if not bbox:
            continue
        tb = text_block_from_bbox(page, bbox)
        if tb:
            blocks.append(tb)
    if not blocks:
        plain = (page.get_text("text") or "").strip()
        if plain:
            blocks.append(TextBlock(text=plain, size=12.0, is_bold=False, runs=[]))
    return blocks
