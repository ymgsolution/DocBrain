from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DocBrain API"
    environment: str = "development"

    database_url: str = ""

    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    storage_root: str = "uploads"
    max_upload_size_mb: int = 25
    allowed_extensions: str = "pdf,doc,docx,xls,xlsx,ppt,pptx,txt,md,csv,png,jpg"

    cors_origins: str = "http://localhost:3000"

    # AI feature track — empty gemini_api_key means the metadata-generation
    # handler is simply not registered by app/ai_jobs/main.py (extraction
    # keeps working either way; see AIProvider/GeminiProvider).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    ai_request_timeout_seconds: float = 30.0
    ai_max_retries: int = 3
    ai_max_extracted_text_chars: int = 20_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
