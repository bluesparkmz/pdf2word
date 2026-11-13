"""Table cell spans from PyMuPDF refine / extract."""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf as fitz


@dataclass(frozen=True)
class SpanCellInfo:
    text: str
    colspan: int = 1
    rowspan: int = 1
    tag: str = "td"
    bold: bool = False
    color_rgb: tuple[int, int, int] | None = None
    fill_rgb: tuple[int, int, int] | None = None
    font_pt: float | None = None


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    return "\n".join(line.strip() for line in str(text).splitlines()).strip()


def span_rows_from_table(page: fitz.Page, table) -> list[list[SpanCellInfo]] | None:
    """Placement grid from find_tables(refine=True), or None."""
    from services.pdf_style import dominant_run_style, fill_behind_rect, runs_to_plain, styled_runs_in_rect

    placements = getattr(table, "placements", None)
    if placements:
        grid: list[list[SpanCellInfo]] = []
        for row in placements:
            cells: list[SpanCellInfo] = []
            for cell in row:
                text = _clean_text(cell.text)
                bold, color, size = False, None, 10.0
                fill = None
                bbox = getattr(cell, "bbox", None)
                if bbox is not None:
                    rect = fitz.Rect(bbox)
                    runs = styled_runs_in_rect(page, rect)
                    if runs:
                        text = runs_to_plain(runs) or text
                        bold, color, size = dominant_run_style(runs)
                    fill = fill_behind_rect(page, rect)
                cells.append(
                    SpanCellInfo(
                        text=text,
                        colspan=max(1, int(cell.colspan)),
                        rowspan=max(1, int(cell.rowspan)),
                        tag=str(getattr(cell, "tag", "td") or "td"),
                        bold=bold or str(getattr(cell, "tag", "")) == "th",
                        color_rgb=color,
                        fill_rgb=fill,
                        font_pt=size,
                    )
                )
            grid.append(cells)
        return grid
    return None


def flat_rows_with_styles(page: fitz.Page, table) -> list[list[SpanCellInfo]]:
    """Grelha simples com estilos por célula."""
    from services.pdf_style import dominant_run_style, fill_behind_rect, runs_to_plain, styled_runs_in_rect

    raw = table.extract()
    out: list[list[SpanCellInfo]] = []
    for ri, row in enumerate(table.rows):
        cells: list[SpanCellInfo] = []
        for ci, cell_bbox in enumerate(row.cells):
            if cell_bbox is None:
                cells.append(SpanCellInfo(text=""))
                continue
            rect = fitz.Rect(cell_bbox)
            runs = styled_runs_in_rect(page, rect)
            fallback = ""
            if raw and ri < len(raw) and ci < len(raw[ri]):
                fallback = _clean_text(raw[ri][ci])
            text = runs_to_plain(runs) if runs else fallback
            bold, color, size = dominant_run_style(runs) if runs else (False, None, 10.0)
            fill = fill_behind_rect(page, rect)
            cells.append(
                SpanCellInfo(
                    text=text,
                    bold=bold,
                    color_rgb=color,
                    fill_rgb=fill,
                    font_pt=size,
                )
            )
        out.append(cells)
    return out


def flat_rows_from_table(table) -> list[list[str]]:
    raw = table.extract()
    if not raw:
        return []
    return [[_clean_text(cell) for cell in row] for row in raw]
