"""OCR for scanned PDF pages via Tesseract."""

from __future__ import annotations

import shutil
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
import pytesseract


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None or Path(
        getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    ).exists()


def ocr_pdf_pages(
    pdf_path: str,
    page_indices: list[int] | None,
    lang: str,
    dpi: int,
) -> dict[int, str]:
    if not tesseract_available():
        raise RuntimeError(
            "Tesseract OCR não encontrado. Instale Tesseract e adicione ao PATH "
            "ou defina PDF2WORD_TESSERACT_CMD no .env"
        )

    if page_indices is None:
        images = convert_from_path(pdf_path, dpi=dpi)
        indices = list(range(len(images)))
    else:
        images = []
        indices = []
        for idx in page_indices:
            batch = convert_from_path(pdf_path, dpi=dpi, first_page=idx + 1, last_page=idx + 1)
            if batch:
                images.append(batch[0])
                indices.append(idx)

    out: dict[int, str] = {}
    config = "--oem 3 --psm 6"
    for idx, img in zip(indices, images, strict=True):
        if not isinstance(img, Image.Image):
            continue
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        out[idx] = text.strip()
    return out
