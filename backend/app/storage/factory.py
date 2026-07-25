from app.core.config import get_settings
from app.storage.local_adapter import LocalFileSystemStorage
from app.storage.port import StoragePort


def get_storage(provider: str | None = None) -> StoragePort:
    """Single place that picks the storage adapter, replacing the previous
    pattern of every call site constructing LocalFileSystemStorage directly.

    provider defaults to settings.storage_provider (the "what do new writes
    use" flag) — but callers reading an *existing* file must pass the
    version's own DocumentVersion.storage_provider instead, so a global
    STORAGE_PROVIDER flip doesn't strand versions written under the old
    provider (see document_version.py's storage_provider column)."""
    name = provider if provider is not None else get_settings().storage_provider
    if name == "supabase":
        from app.storage.supabase_adapter import SupabaseStorageAdapter

        return SupabaseStorageAdapter()
    return LocalFileSystemStorage()
