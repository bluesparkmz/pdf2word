from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDF2WORD_", env_file=".env", extra="ignore")

    upload_dir: Path = Path("data/uploads")
    output_dir: Path = Path("data/outputs")
    tesseract_cmd: str | None = None
    default_ocr_lang: str = "por+eng"
    ocr_dpi: int = 300
    min_text_chars_per_page: int = 40
    max_upload_mb: int = 50
    cleanup_outputs_after_hours: int = 24


settings = Settings()

if settings.tesseract_cmd:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
