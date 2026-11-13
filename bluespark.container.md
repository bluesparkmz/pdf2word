# PDF2Word no container BlueSpark

## Solução: `bs.json`

Este repo inclui **`bs.json`** com pacotes de sistema só para o pdf2word:

- `tesseract-ocr`, `tesseract-ocr-por`, `tesseract-ocr-eng`
- `poppler-utils`

No redeploy, o Docker Manager BlueSpark gera o Dockerfile FastAPI **com esses pacotes** — sem alterar outros projetos.

Alternativa: `"useRepoDockerfile": true` e usar o `Dockerfile` deste repositório.

Documentação completa: `BlueSpark Cloud/bluesparkcloud/docs/bs-json.md`.

## Verificação

`GET /health` → `"tesseract": true`.

## Sem OCR

Modo **Automático** ou **Só texto nativo** para PDFs digitais (não precisa Tesseract).
