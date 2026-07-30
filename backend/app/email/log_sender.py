import logging

logger = logging.getLogger(__name__)


class LoggingEmailSender:
    """Used whenever no RESEND_API_KEY is configured.

    Deliberately a real, working adapter rather than a crash: local
    development, CI and the test suite all run without email credentials,
    and invitations remain fully usable through the copyable link. The log
    line includes the body so a developer can still follow the flow.
    """

    def send(self, *, to: str, subject: str, html: str, text: str) -> None:
        logger.info("email not sent (no RESEND_API_KEY) — to=%s subject=%r\n%s", to, subject, text)
