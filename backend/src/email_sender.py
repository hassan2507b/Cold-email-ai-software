import smtplib
import logging
import threading
import time
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

logger = logging.getLogger(__name__)

def append_system_signature(ai_body: str) -> str:
    """Appends clean personal sender signature and human opt-out note."""
    sender_name = settings.SENDER_NAME.strip() or "Hassan"
    company_name = settings.COMPANY_NAME.strip()
    
    sig = f"\n\nBest regards,\n{sender_name}"
    if company_name:
        sig += f"\n{company_name}"
    sig += "\n\nPS: If you're not interested, just reply 'stop' or 'unsubscribe' and I will not follow up."
    return ai_body.strip() + sig

class SMTPSessionManager:
    """Maintains an active authenticated SMTP session during batches to avoid reconnecting on every email."""
    def __init__(self):
        self._server = None
        self._last_used = 0
        self._lock = threading.Lock()

    def _connect(self):
        if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
            raise ValueError(
                "SMTP credentials not configured. Please set SMTP_EMAIL and SMTP_PASSWORD in backend/.env."
            )
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        return server

    def get_server(self):
        now = time.time()
        if self._server is not None:
            # If idle for more than 45 seconds, refresh connection
            if now - self._last_used > 45:
                self.close()
            else:
                try:
                    status = self._server.noop()[0]
                    if status == 250:
                        self._last_used = now
                        return self._server
                except Exception:
                    self.close()

        self._server = self._connect()
        self._last_used = now
        return self._server

    def close(self):
        if self._server is not None:
            try:
                self._server.quit()
            except Exception:
                pass
            self._server = None

    def send(self, recipient: str, subject: str, full_body: str):
        with self._lock:
            # Clean plain-text RFC message (avoids empty multipart structures flagged by spam filters)
            msg = MIMEText(full_body, "plain", "utf-8")
            from_header = f"{settings.SENDER_NAME} <{settings.SMTP_EMAIL}>" if settings.SENDER_NAME else settings.SMTP_EMAIL
            msg["From"] = from_header
            msg["To"] = recipient
            msg["Subject"] = subject
            msg["Reply-To"] = settings.SMTP_EMAIL
            msg["Date"] = email.utils.formatdate(localtime=True)
            domain = settings.SMTP_EMAIL.split("@")[-1] if "@" in settings.SMTP_EMAIL else "gmail.com"
            msg["Message-ID"] = email.utils.make_msgid(domain=domain)

            try:
                server = self.get_server()
                server.send_message(msg, from_addr=settings.SMTP_EMAIL, to_addrs=[recipient])
            except Exception as e:
                logger.warning(f"Cached SMTP connection reset ({e}), reconnecting fresh...")
                self.close()
                server = self.get_server()
                server.send_message(msg, from_addr=settings.SMTP_EMAIL, to_addrs=[recipient])

            self._last_used = time.time()
            logger.info(f"Successfully sent cold email to {recipient}")

smtp_manager = SMTPSessionManager()

def send_smtp_email(recipient: str, subject: str, full_body: str) -> None:
    smtp_manager.send(recipient, subject, full_body)
