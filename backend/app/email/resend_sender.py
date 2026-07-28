import logging

import httpx

from app.email.port import EmailError

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.resend.com/emails"
# Long enough for a normal API call, short enough that a hanging provider
# can't stall the request that triggered it.
_TIMEOUT_SECONDS = 10.0


class ResendEmailSender:
    """Transactional email via Resend's HTTP API.

    Called directly with httpx rather than through the `resend` SDK: it's a
    single JSON POST, and this keeps one less dependency (and one less
    thing to keep updated) for something this small. Same reasoning as
    using boto3's S3 API rather than the Supabase SDK for storage.
    """

    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self._sender = sender

    def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        try:
            response = httpx.post(
                _ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"from": self._sender, "to": [to], "subject": subject, "html": html, "text": text},
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise EmailError(f"Could not reach Resend: {exc}") from exc

        if response.status_code >= 400:
            # The body carries Resend's actual reason (unverified domain,
            # invalid recipient, rate limit), which is what someone
            # debugging a non-delivery actually needs.
            raise EmailError(f"Resend rejected the message ({response.status_code}): {response.text[:300]}")

        logger.info("email sent to=%s subject=%r", to, subject)
