# PDF2Word Advanced

API **FastAPI** para converter PDF em Word (`.docx`) com:

- **Texto nativo** via PyMuPDF (blocos, tamanhos, negrito aproximado)
- **OCR** com Tesseract em páginas escaneadas ou modo forçado
- **Modo híbrido**: só aplica OCR onde falta texto legível
- Interface web em `/` e documentação OpenAPI em `/docs`

## Requisitos

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) no PATH (e pacotes `por`, `eng`, etc.)
- **Poppler** (para `pdf2image` no Windows): instale e adicione `pdftoppm` ao PATH,  
  ou defina `POPPLER_PATH` antes de correr a app

### Windows (exemplo)

1. Tesseract: instalador UB Mannheim  
2. Poppler: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) — extrair e adicionar `Library\bin` ao PATH  
3. Copiar `.env.example` para `.env` e ajustar `PDF2WORD_TESSERACT_CMD` se necessário

## Instalação

```powershell
cd "D:\BlueSpark MZ\pdf2word"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Docker / BlueSpark Cloud

O ficheiro **`bs.json`** pede ao Docker Manager os pacotes OCR **só neste serviço** (ver `bluespark.container.md` e `docs/bs-json.md` na BlueSpark Cloud).

Build local:

```bash
docker build -t pdf2word .
```

## Executar (local)

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- UI: http://localhost:8000  
- Swagger: http://localhost:8000/docs  

## API

`POST /convert` — `multipart/form-data`

| Campo      | Descrição |
|-----------|-----------|
| `file`    | PDF |
| `ocr_mode`| `auto` \| `force` \| `off` |
| `ocr_lang`| Idiomas Tesseract, ex. `por+eng` |
| `dpi`     | 72–600 (0 = 300) |

Resposta inclui `download` com URL para `GET /download/{job_id}`.

## Modos

- **auto**: se mais de metade das páginas têm pouco texto, OCR global; senão híbrido página a página
- **force**: OCR em todas as páginas (digitalizações puras)
- **off**: apenas camada de texto do PDF (sem Tesseract)
