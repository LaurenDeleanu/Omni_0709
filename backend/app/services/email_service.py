import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger("successcore.email")

SMTP_HOST = settings.SMTP_HOST or "smtp.gmail.com"
SMTP_PORT = settings.SMTP_PORT or 587
SMTP_USER = settings.SMTP_USER or ""
SMTP_PASS = settings.SMTP_PASSWORD or ""


async def send_email(to: str, subject: str, body: str, html: bool = False) -> bool:
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP not configured — email skipped")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))

        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _smtp_send, msg)
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email failed to {to}: {e}")
        return False


def _smtp_send(msg):
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
