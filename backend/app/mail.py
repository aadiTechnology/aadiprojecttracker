"""Outgoing email over SMTP (Brevo relay in staging). Configure with SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
SMTP_FROM, SMTP_USE_TLS (true = STARTTLS on 587; port 465 uses implicit SSL) and APP_BASE_URL (links inside emails)."""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("tracker.mail")


def _cfg():
    return {"host": os.environ.get("SMTP_HOST", ""), "port": int(os.environ.get("SMTP_PORT", "587") or 587),
            "user": os.environ.get("SMTP_USER", ""), "password": os.environ.get("SMTP_PASSWORD", ""),
            "sender": os.environ.get("SMTP_FROM", ""), "tls": os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
            "backend": os.environ.get("EMAIL_BACKEND", "smtp")}


def configured() -> bool:
    c = _cfg()
    return c["backend"] == "smtp" and bool(c["host"] and c["sender"])


def public_url() -> str:
    return os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")


def send(to: str, subject: str, text: str) -> bool:
    """True when the server accepted the message. Never raises; never logs the body or credentials."""
    c = _cfg()
    if not configured():
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = c["sender"], to, subject
    msg.set_content(text)
    try:
        if c["port"] == 465:
            smtp = smtplib.SMTP_SSL(c["host"], c["port"], timeout=15, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(c["host"], c["port"], timeout=15)
        with smtp:
            if c["port"] != 465 and c["tls"]:
                smtp.starttls(context=ssl.create_default_context())
            if c["user"]:
                smtp.login(c["user"], c["password"])
            smtp.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001 - email trouble must not fail the request that triggered it
        log.warning("email to %s failed: %s", to.split("@")[-1], type(e).__name__)
        return False


def invite_email(name: str, org: str, token: str):
    link = f"{public_url()}/reset?token={token}"
    return (f"You have been invited to {org} on Aadi Project Tracker",
            f"Hello {name},\n\nYou have been invited to {org} on Aadi Project Tracker. Choose your password within 7 days:\n{link}\n\nThen sign in at {public_url()}.\n")


def reset_email(name: str, token: str):
    link = f"{public_url()}/reset?token={token}"
    return ("Reset your Aadi Project Tracker password",
            f"Hello {name},\n\nUse this link within 1 hour to choose a new password:\n{link}\n\nIf you did not ask for this, ignore this email.\n")
