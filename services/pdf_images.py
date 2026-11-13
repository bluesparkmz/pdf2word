"""Extract embedded images from PDF pages."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pymupdf as fitz
from PIL import Image

MIN_IMAGE_PT = 22.0


@dataclass
class PdfImage:
    y0: float
    data: bytes
    ext: str
    width_pt: float
    height_pt: float


def _inside_table(rect: fitz.Rect, table_rects: list[fitz.Rect]) -> bool:
    c = ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
    for tr in table_rects:
        if tr.contains(c):
            return True
    return False


def _normalize_bytes(raw: bytes, ext: str) -> tuple[bytes, str]:
    ext = (ext or "png").lower()
    if ext in {"jpeg", "jpg", "png", "gif", "bmp"}:
        return raw, "jpeg" if ext in {"jpg", "jpeg"} else ext
    try:
        img = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), "png"
    except Exception:
        return raw, ext


def extract_page_images(page: fitz.Page, table_rects: list[fitz.Rect]) -> list[PdfImage]:
    doc = page.parent
    if doc is None:
        return []
    found: list[PdfImage] = []
    seen_rects: set[tuple[int, int, int, int]] = set()

    for entry in page.get_images(full=True):
        xref = entry[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            continue
        if not rects:
            continue
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        raw = extracted.get("image")
        if not raw:
            continue
        data, ext = _normalize_bytes(raw, str(extracted.get("ext", "png")))

        for rect in rects:
            if isinstance(rect, (list, tuple)):
                r = fitz.Rect(rect)
            else:
                r = fitz.Rect(rect)
            if r.width < MIN_IMAGE_PT or r.height < MIN_IMAGE_PT:
                continue
            if _inside_table(r, table_rects):
                continue
            key = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
            if key in seen_rects:
                continue
            seen_rects.add(key)
            found.append(
                PdfImage(
                    y0=r.y0,
                    data=data,
                    ext=ext,
                    width_pt=r.width,
                    height_pt=r.height,
                )
            )

    found.sort(key=lambda img: img.y0)
    return found
