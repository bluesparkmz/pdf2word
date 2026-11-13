"""Dimensões de tabelas a partir da grelha PDF (pontos)."""

from __future__ import annotations

import pymupdf as fitz


def column_widths_pt(table) -> list[float]:
    """Larguras de coluna em pontos, da geometria das células."""
    edges: list[float] = []
    for row in table.rows:
        for cell in row.cells:
            if not cell:
                continue
            r = fitz.Rect(cell)
            edges.extend([r.x0, r.x1])
    if not edges:
        bbox = table.bbox
        if bbox and table.col_count:
            total = fitz.Rect(bbox).width
            return [total / table.col_count] * table.col_count
        return []
    xs = sorted(set(round(x, 2) for x in edges))
    widths = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    return [w for w in widths if w > 0.5]


def table_bbox_width_pt(table) -> float:
    bbox = table.bbox
    if bbox:
        return fitz.Rect(bbox).width
    widths = column_widths_pt(table)
    return sum(widths) if widths else 0.0
