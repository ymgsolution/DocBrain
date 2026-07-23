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


@lru_cache
def get_settings() -> Settings:
    return Settings()
