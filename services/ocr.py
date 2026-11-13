"""OCR for scanned PDF pages via Tesseract."""

from __future__ import annotations

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

from services.tesseract_setup import poppler_path, tesseract_available, tesseract_cmd_resolved


def ocr_unavailable_message() -> str:
    return (
        "Tesseract OCR não encontrado no servidor. "
        "Instale tesseract-ocr (+ por, eng), defina PDF2WORD_TESSERACT_CMD no .env, "
        "ou use modo OCR «Automático» / «Só texto nativo» para PDFs com texto."
    )


def ocr_pdf_pages(
    pdf_path: str,
    page_indices: list[int] | None,
    lang: str,
    dpi: int,
) -> dict[int, str]:
    if not tesseract_available():
        raise RuntimeError(ocr_unavailable_message())

    poppler = poppler_path()
    convert_kw: dict = {"dpi": dpi}
    if poppler:
        convert_kw["poppler_path"] = poppler

    if page_indices is None:
        images = convert_from_path(pdf_path, **convert_kw)
        indices = list(range(len(images)))
    else:
        images = []
        indices = []
        for idx in page_indices:
            batch = convert_from_path(
                pdf_path,
                first_page=idx + 1,
                last_page=idx + 1,
                **convert_kw,
            )
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


def ocr_diagnostics() -> dict:
    return {
        "available": tesseract_available(),
        "tesseract_cmd": tesseract_cmd_resolved(),
        "poppler_path": poppler_path(),
    }
