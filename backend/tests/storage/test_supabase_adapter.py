"""SupabaseStorageAdapter tested against a fake stand-in for the boto3 S3
client — no real network call, same monkeypatched-SDK-boundary style used
for GeminiProvider (there's no pure in-process equivalent to construct for
an HTTP call, so the seam being faked is the client itself).
"""

import io
from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.storage.supabase_adapter import SupabaseStorageAdapter, SupabaseStorageConfigError, _validate_settings

_VALID_CONFIG = {
    "supabase_storage_endpoint": "https://real-project.supabase.co/storage/v1/s3",
    "supabase_storage_region": "ap-south-1",
    "supabase_storage_bucket": "DocBrain",
    "supabase_storage_access_key_id": "access-key",
    "supabase_storage_secret_access_key": "secret-key",
}


def _settings(**overrides: str) -> Settings:
    # dict[str, Any], not dict[str, str]: Settings also has int/float fields,
    # so a str-typed splat doesn't type-check against its constructor.
    config: dict[str, Any] = {**_VALID_CONFIG, **overrides}
    return Settings(**config)


def test_a_placeholder_endpoint_is_rejected_with_a_useful_message() -> None:
    """The exact failure hit while deploying the worker: the endpoint was
    left as .env.example's `https://[project-ref].supabase.co/...`. Left to
    boto3, urllib reads the bracketed host as an IPv6 literal and raises
    `ValueError: Invalid IPv6 URL` — a message that names neither the
    setting nor the real mistake."""
    with pytest.raises(SupabaseStorageConfigError) as exc_info:
        _validate_settings(_settings(supabase_storage_endpoint="https://[project-ref].supabase.co/storage/v1/s3"))

    message = str(exc_info.value)
    assert "SUPABASE_STORAGE_ENDPOINT" in message  # names the offending variable
    assert "placeholder" in message


def test_missing_settings_are_named_individually() -> None:
    with pytest.raises(SupabaseStorageConfigError) as exc_info:
        _validate_settings(_settings(supabase_storage_bucket="", supabase_storage_access_key_id="   "))

    message = str(exc_info.value)
    assert "SUPABASE_STORAGE_BUCKET" in message
    assert "SUPABASE_STORAGE_ACCESS_KEY_ID" in message
    # ...and points at the way out, since local storage is a valid choice.
    assert "STORAGE_PROVIDER=local" in message


def test_a_complete_config_passes_validation() -> None:
    _validate_settings(_settings())  # must not raise


def _make_adapter() -> SupabaseStorageAdapter:
    adapter = SupabaseStorageAdapter.__new__(SupabaseStorageAdapter)
    adapter._bucket = "test-bucket"
    return adapter


class _FakeStreamingBody:
    """Mirrors botocore.response.StreamingBody's real, observed shape: a
    forward-only .read(), no working .seek() — calling it raises
    io.UnsupportedOperation, exactly what pypdf hit against the real
    adapter before this fix."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, amt: int | None = None) -> bytes:
        return self._data

    def seek(self, *args: object, **kwargs: object) -> int:
        raise io.UnsupportedOperation("seek")


def test_open_for_read_returns_a_genuinely_seekable_stream() -> None:
    """The regression this test exists for: open_for_read used to return
    the raw StreamingBody directly, which satisfied BinaryIO's read()-based
    usage (downloads worked fine) but broke the moment anything needed to
    seek — silently failing text extraction (pypdf requires seeking to a
    PDF's trailer/xref table) for every document uploaded after the move to
    Supabase, which in turn meant GENERATE_METADATA/GENERATE_EMBEDDING were
    never even enqueued."""
    adapter = _make_adapter()
    content = b"%PDF-fake-content-for-seek-test"
    adapter._client = type(
        "_FakeClient", (), {"get_object": lambda self, Bucket, Key: {"Body": _FakeStreamingBody(content)}}
    )()

    with adapter.open_for_read("documents/some-id/v1__file.pdf") as stream:
        assert stream.seekable()
        stream.seek(0, 2)  # exactly what pypdf's _basic_validation does first
        assert stream.tell() == len(content)
        stream.seek(0)
        assert stream.read() == content


def test_open_for_read_raises_file_not_found_on_404() -> None:
    adapter = _make_adapter()

    def raise_404(self: object, Bucket: str, Key: str) -> None:
        raise ClientError(
            {
                "Error": {"Code": "", "Message": ""},
                "ResponseMetadata": {
                    "HTTPStatusCode": 404,
                    "HTTPHeaders": {},
                    "RequestId": "",
                    "HostId": "",
                    "RetryAttempts": 0,
                },
            },
            "GetObject",
        )

    adapter._client = type("_FakeClient", (), {"get_object": raise_404})()

    with pytest.raises(FileNotFoundError):
        adapter.open_for_read("documents/does-not-exist/nope.pdf")


def test_open_for_read_reraises_non_404_client_errors() -> None:
    adapter = _make_adapter()

    def raise_500(self: object, Bucket: str, Key: str) -> None:
        raise ClientError(
            {
                "Error": {"Code": "", "Message": ""},
                "ResponseMetadata": {
                    "HTTPStatusCode": 500,
                    "HTTPHeaders": {},
                    "RequestId": "",
                    "HostId": "",
                    "RetryAttempts": 0,
                },
            },
            "GetObject",
        )

    adapter._client = type("_FakeClient", (), {"get_object": raise_500})()

    with pytest.raises(ClientError):
        adapter.open_for_read("documents/some-id/v1__file.pdf")
