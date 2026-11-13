"""Extract embedded images from PDF pages."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pymupdf as fitz
from PIL import Image

MIN_IMAGE_PT = 22.0
RENDER_DPI = 200


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


def _flatten_alpha_to_white(raw: bytes, ext: str) -> tuple[bytes, str]:
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return raw, ext
    background = Image.new("RGBA", img.size, (255, 255, 255, 255))
    background.alpha_composite(img)
    flat = background.convert("RGB")
    buf = io.BytesIO()
    flat.save(buf, format="PNG")
    return buf.getvalue(), "png"


def _render_rect_png(page: fitz.Page, rect: fitz.Rect) -> bytes:
    """Renderiza a região visível no PDF (fundo branco, sem preto de alpha)."""
    scale = RENDER_DPI / 72.0
    matrix = fitz.Matrix(scale, scale)
    clip = rect + (-1, -1, 1, 1)
    pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
    return pix.tobytes("png")


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

        for rect in rects:
            r = fitz.Rect(rect) if not isinstance(rect, fitz.Rect) else rect
            if r.width < MIN_IMAGE_PT or r.height < MIN_IMAGE_PT:
                continue
            if _inside_table(r, table_rects):
                continue
            key = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
            if key in seen_rects:
                continue
            seen_rects.add(key)

            try:
                data = _render_rect_png(page, r)
                ext = "png"
            except Exception:
                try:
                    extracted = doc.extract_image(xref)
                    raw = extracted.get("image")
                    if not raw:
                        continue
                    data, ext = _flatten_alpha_to_white(raw, str(extracted.get("ext", "png")))
                except Exception:
                    continue

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
