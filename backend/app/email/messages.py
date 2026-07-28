"""Email bodies, kept apart from the services that trigger them.

Every message ships both HTML and plain text — some clients render only
text, and a link that arrives as an unclickable blob of markup is a support
request waiting to happen.

Deliberately plain HTML with inline styles: email clients strip <style>
blocks and understand almost no modern CSS, so a template engine or the
app's own design system would buy nothing here.
"""

_WRAPPER = """\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
            max-width:480px;margin:0 auto;padding:24px;color:#111827">
  <p style="font-size:18px;font-weight:600;margin:0 0 16px">DocBrain</p>
  {body}
  <p style="color:#6b7280;font-size:12px;margin-top:28px;border-top:1px solid #e5e7eb;padding-top:14px">
    If you weren't expecting this email, you can safely ignore it.
  </p>
</div>"""

_BUTTON = """\
<p style="margin:22px 0">
  <a href="{url}" style="background:#4f46e5;color:#fff;text-decoration:none;
     padding:11px 20px;border-radius:8px;display:inline-block;font-weight:500">{label}</a>
</p>
<p style="color:#6b7280;font-size:12px;word-break:break-all">
  Or paste this into your browser:<br>{url}
</p>"""


def invitation_email(*, invited_by: str, role: str, url: str, expires_days: int) -> tuple[str, str, str]:
    """Returns (subject, html, text)."""
    subject = "You've been invited to DocBrain"
    friendly_role = role.capitalize()
    body = (
        f"<p><strong>{invited_by}</strong> has invited you to join DocBrain as a "
        f"<strong>{friendly_role}</strong>.</p>"
        "<p>Choose a password to set up your account:</p>"
        + _BUTTON.format(url=url, label="Accept invitation")
        + f"<p style='color:#6b7280;font-size:13px'>This invitation expires in {expires_days} days.</p>"
    )
    text = (
        f"{invited_by} has invited you to join DocBrain as a {friendly_role}.\n\n"
        f"Set up your account here:\n{url}\n\n"
        f"This invitation expires in {expires_days} days.\n\n"
        "If you weren't expecting this email, you can safely ignore it."
    )
    return subject, _WRAPPER.format(body=body), text


def password_reset_email(*, url: str, expires_minutes: int) -> tuple[str, str, str]:
    subject = "Reset your DocBrain password"
    body = (
        "<p>We received a request to reset your DocBrain password.</p>"
        + _BUTTON.format(url=url, label="Reset password")
        + f"<p style='color:#6b7280;font-size:13px'>This link expires in {expires_minutes} minutes "
        "and can only be used once.</p>"
    )
    text = (
        "We received a request to reset your DocBrain password.\n\n"
        f"Reset it here:\n{url}\n\n"
        f"This link expires in {expires_minutes} minutes and can only be used once.\n\n"
        "If you didn't request this, you can safely ignore this email — your password won't change."
    )
    return subject, _WRAPPER.format(body=body), text
