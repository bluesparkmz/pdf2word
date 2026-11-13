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


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    return "\n".join(line.strip() for line in str(text).splitlines()).strip()


def span_rows_from_table(table) -> list[list[SpanCellInfo]] | None:
    """Placement grid from find_tables(refine=True), or None."""
    placements = getattr(table, "placements", None)
    if placements:
        return [
            [
                SpanCellInfo(
                    text=_clean_text(cell.text),
                    colspan=max(1, int(cell.colspan)),
                    rowspan=max(1, int(cell.rowspan)),
                    tag=str(getattr(cell, "tag", "td") or "td"),
                )
                for cell in row
            ]
            for row in placements
        ]
    return None


def flat_rows_from_table(table) -> list[list[str]]:
    raw = table.extract()
    if not raw:
        return []
    return [[_clean_text(cell) for cell in row] for row in raw]
