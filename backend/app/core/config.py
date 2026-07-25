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

    # "local" (default — LocalFileSystemStorage, backend/uploads/) or
    # "supabase" (SupabaseStorageAdapter, S3-compatible). See app/storage/
    # factory.py. Local stays the default so dev/test never needs live
    # Supabase Storage credentials.
    storage_provider: str = "local"
    supabase_storage_endpoint: str = ""
    supabase_storage_region: str = ""
    supabase_storage_bucket: str = ""
    supabase_storage_access_key_id: str = ""
    supabase_storage_secret_access_key: str = ""

    cors_origins: str = "http://localhost:3000"

    # AI feature track — empty gemini_api_key means the metadata-generation
    # handler is simply not registered by app/ai_jobs/main.py (extraction
    # keeps working either way; see AIProvider/GeminiProvider).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    ai_request_timeout_seconds: float = 30.0
    ai_max_retries: int = 3
    ai_max_extracted_text_chars: int = 20_000
    # A 429 (quota exhausted) job gets its own, much longer backoff than a
    # normal transient failure (see ai_jobs/repository.py) — retrying a
    # quota error on the normal 30s/60s/120s/240s schedule just burns more
    # of an already-exhausted free-tier budget on requests that are certain
    # to fail again. Same exponential-with-cap shape as the generic backoff,
    # just starting much higher.
    ai_quota_backoff_base_seconds: int = 300
    ai_quota_backoff_cap_seconds: int = 3600

    # Similar Document Detection track — same gemini_api_key gate as metadata
    # generation (app/ai_jobs/main.py). A separate, smaller char limit than
    # ai_max_extracted_text_chars: embedding models have a much lower input
    # token ceiling than generation models.
    gemini_embedding_model: str = "gemini-embedding-001"
    ai_embedding_dimensions: int = 768
    ai_embedding_max_chars: int = 8_000
    # Below this cosine similarity, a "similar" document is more likely noise
    # than a genuinely related document (e.g. two documents that just happen
    # to share generic corporate boilerplate) — filtered out rather than
    # shown, same "show nothing rather than a weak/misleading result"
    # philosophy as the rest of this feature.
    similarity_min_score: float = 0.80


@lru_cache
def get_settings() -> Settings:
    return Settings()
