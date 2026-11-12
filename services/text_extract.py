"""Extract text and layout hints from native PDF text layers."""

from dataclasses import dataclass

import fitz


@dataclass
class TextBlock:
    text: str
    size: float
    is_bold: bool


def extract_page_blocks(page: fitz.Page) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines_text: list[str] = []
        max_size = 0.0
        bold = False
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            line_parts = []
            for span in spans:
                t = span.get("text", "")
                if not t:
                    continue
                size = float(span.get("size", 12))
                max_size = max(max_size, size)
                flags = int(span.get("flags", 0))
                if flags & 2**4:
                    bold = True
                line_parts.append(t)
            if line_parts:
                lines_text.append("".join(line_parts))
        joined = "\n".join(lines_text).strip()
        if joined:
            blocks.append(TextBlock(text=joined, size=max_size or 12.0, is_bold=bold))
    if not blocks:
        plain = (page.get_text("text") or "").strip()
        if plain:
            blocks.append(TextBlock(text=plain, size=12.0, is_bold=False))
    return blocks
