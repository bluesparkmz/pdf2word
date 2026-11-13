"""Cores e preenchimentos a partir do PDF (texto + vector drawings)."""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf as fitz


@dataclass
class TextRun:
    text: str
    size: float
    bold: bool
    color_rgb: tuple[int, int, int] | None = None


def srgb_to_rgb(color: int) -> tuple[int, int, int]:
    return ((color >> 16) & 255, (color >> 8) & 255, color & 255)


def _normalize_fill_color(fill) -> tuple[int, int, int] | None:
    if fill is None:
        return None
    if isinstance(fill, (list, tuple)) and len(fill) >= 3:
        parts = fill[:3]
        if all(isinstance(x, (int, float)) for x in parts):
            if all(0 <= x <= 1 for x in parts):
                return tuple(int(x * 255) for x in parts)
            return tuple(int(x) for x in parts)
    if isinstance(fill, int):
        return srgb_to_rgb(fill)
    return None


def fill_behind_rect(page: fitz.Page, rect: fitz.Rect) -> tuple[int, int, int] | None:
    """Cor de fundo dominante (rectângulos vector) sob a célula."""
    best: tuple[int, int, int] | None = None
    best_area = 0.0
    target = rect * 0.98
    for path in page.get_drawings():
        rgb = _normalize_fill_color(path.get("fill"))
        if rgb is None or rgb == (255, 255, 255):
            continue
        area = 0.0
        pr = path.get("rect")
        if pr is not None:
            r = fitz.Rect(pr)
            inter = target & r
            if not inter.is_empty:
                area = inter.get_area()
        else:
            for item in path.get("items", []):
                if not item:
                    continue
                op = item[0]
                if op == "re" and len(item) > 1:
                    r = fitz.Rect(item[1])
                    inter = target & r
                    if not inter.is_empty:
                        area = max(area, inter.get_area())
        if area > best_area:
            best_area = area
            best = rgb
    return best if best_area > 50 else None


def styled_runs_in_rect(page: fitz.Page, rect: fitz.Rect) -> list[TextRun]:
    """Texto com cor/negrito dentro de um bbox."""
    runs: list[TextRun] = []
    data = page.get_text("dict", clip=rect, flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue
                size = float(span.get("size", 11))
                bold = bool(int(span.get("flags", 0)) & 16)
                color = int(span.get("color", 0))
                rgb = srgb_to_rgb(color)
                if rgb == (0, 0, 0):
                    rgb = None
                runs.append(TextRun(text=text, size=size, bold=bold, color_rgb=rgb))
    return runs


def runs_to_plain(runs: list[TextRun]) -> str:
    return "".join(r.text for r in runs).strip()


def dominant_run_style(runs: list[TextRun]) -> tuple[bool, tuple[int, int, int] | None, float]:
    if not runs:
        return False, None, 11.0
    bold = any(r.bold for r in runs)
    colors = [r.color_rgb for r in runs if r.color_rgb]
    color = colors[0] if colors else None
    size = max(r.size for r in runs)
    return bold, color, size
