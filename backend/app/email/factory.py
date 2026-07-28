from app.core.config import get_settings
from app.email.log_sender import LoggingEmailSender
from app.email.port import EmailSender


def get_email_sender() -> EmailSender:
    """Single place that picks the adapter, mirroring app/storage/factory.py.

    No key configured is a valid setup, not an error — see LoggingEmailSender.
    """
    settings = get_settings()
    if settings.resend_api_key:
        from app.email.resend_sender import ResendEmailSender

        return ResendEmailSender(settings.resend_api_key, settings.email_from)
    return LoggingEmailSender()
