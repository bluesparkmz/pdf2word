"""
PDF2Word — API FastAPI com extração nativa, OCR híbrido e exportação DOCX.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from config import settings
from services.converter import OcrMode, convert_pdf_to_docx
from services.ocr import tesseract_available

app = FastAPI(
    title="PDF2Word Advanced",
    description="Conversão PDF → Word com OCR Tesseract, modo híbrido e análise de páginas.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for d in (settings.upload_dir, settings.output_dir):
    d.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def startup() -> None:
    if settings.tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@app.get("/health")
def health():
    return {
        "status": "ok",
        "tesseract": tesseract_available(),
        "ocr_lang_default": settings.default_ocr_lang,
        "max_upload_mb": settings.max_upload_mb,
    }


@app.post("/convert")
async def convert(
    file: UploadFile = File(..., description="Arquivo PDF"),
    ocr_mode: OcrMode = Form(OcrMode.AUTO),
    ocr_lang: str = Form(default=""),
    dpi: int = Form(default=0, ge=0, le=600),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um ficheiro .pdf")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"PDF excede {settings.max_upload_mb} MB")

    job_id = uuid.uuid4().hex
    pdf_path = settings.upload_dir / f"{job_id}.pdf"
    out_path = settings.output_dir / f"{job_id}.docx"

    async with aiofiles.open(pdf_path, "wb") as f:
        await f.write(content)

    lang = ocr_lang.strip() or settings.default_ocr_lang
    ocr_dpi = dpi if dpi > 0 else settings.ocr_dpi

    try:
        result = convert_pdf_to_docx(
            pdf_path,
            out_path,
            ocr_mode=ocr_mode,
            ocr_lang=lang,
            dpi=ocr_dpi,
        )
    except RuntimeError as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Falha na conversão: {e}") from e
    finally:
        pdf_path.unlink(missing_ok=True)

    return {
        "job_id": job_id,
        "download": f"/download/{job_id}",
        "pages": result.pages,
        "native_pages": result.native_pages,
        "ocr_pages": result.ocr_pages,
        "mode_used": result.mode_used,
        "filename": f"{Path(file.filename).stem}.docx",
    }


@app.get("/download/{job_id}")
def download(job_id: str):
    safe = job_id.replace("/", "").replace("..", "")
    path = settings.output_dir / f"{safe}.docx"
    if not path.is_file():
        raise HTTPException(404, "Documento não encontrado ou expirado")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"converted_{safe}.docx",
    )


@app.get("/", response_class=HTMLResponse)
def ui():
    return """<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PDF2Word Advanced</title>
  <style>
    :root { font-family: system-ui, sans-serif; color: #0f172a; background: #f1f5f9; }
    body { max-width: 520px; margin: 2rem auto; padding: 1.5rem; background: #fff; border-radius: 12px; box-shadow: 0 8px 30px #0001; }
    h1 { font-size: 1.35rem; margin: 0 0 1rem; }
  label { display: block; font-size: 0.85rem; margin: 0.75rem 0 0.25rem; color: #475569; }
  input, select, button { width: 100%; box-sizing: border-box; padding: 0.55rem; margin-top: 0.25rem; }
  button { background: #2563eb; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 1rem; }
  button:disabled { opacity: 0.6; }
  #msg { margin-top: 1rem; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>PDF2Word (OCR avançado)</h1>
  <form id="f">
    <label>PDF<input type="file" name="file" accept=".pdf" required></label>
    <label>Modo OCR
      <select name="ocr_mode">
        <option value="auto">Automático (híbrido)</option>
        <option value="force">Forçar OCR em todas as páginas</option>
        <option value="off">Só texto nativo (sem OCR)</option>
      </select>
    </label>
    <label>Idiomas Tesseract (ex: por+eng)<input name="ocr_lang" placeholder="por+eng"></label>
    <label>DPI (0 = padrão 300)<input type="number" name="dpi" min="0" max="600" value="0"></label>
    <button type="submit">Converter para Word</button>
  </form>
  <p id="msg"></p>
  <script>
    const f = document.getElementById('f');
    const msg = document.getElementById('msg');
    f.addEventListener('submit', async (e) => {
      e.preventDefault();
      msg.textContent = 'A converter...';
      const fd = new FormData(f);
      if (!fd.get('ocr_lang')) fd.delete('ocr_lang');
      const btn = f.querySelector('button');
      btn.disabled = true;
      try {
        const r = await fetch('/convert', { method: 'POST', body: fd });
        const j = await r.json();
        if (!r.ok) throw new Error(j.detail || r.statusText);
        msg.innerHTML = `Pronto: ${j.pages} págs (${j.mode_used}). <a href="${j.download}">Descarregar DOCX</a>`;
      } catch (err) {
        msg.textContent = 'Erro: ' + err.message;
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
