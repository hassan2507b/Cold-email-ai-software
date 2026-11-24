import imaplib
import logging
import re
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parseaddr

from .config import settings
from .database import add_suppressed_recipient, get_last_imap_uid, save_last_imap_uid

logger = logging.getLogger(__name__)


def is_imap_configured() -> bool:
    return bool(settings.IMAP_USERNAME and settings.IMAP_PASSWORD)


def _decoded_header(value: str | None) -> str:
    if not value:
        return ""
    return str(make_header(decode_header(value)))


def _message_text(message) -> str:
    parts = message.walk() if message.is_multipart() else [message]
    text_parts = []
    for part in parts:
        if part.get_content_type() != "text/plain" or part.get_content_disposition() == "attachment":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        text_parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(text_parts)

def _new_reply_text(text: str) -> str:
    quote_markers = re.compile(
        r"(?im)^\s*>|^On .+wrote:\s*$|^-{2,}\s*Original Message\s*-{2,}\s*$|^From:\s*.+$"
    )
    match = quote_markers.search(text)
    return text[:match.start()] if match else text


def process_unsubscribe_message(raw_message: bytes) -> str | None:
    message = message_from_bytes(raw_message)
    sender = parseaddr(_decoded_header(message.get("From")))[1].strip().lower()
    if not sender:
        return None

    subject = _decoded_header(message.get("Subject"))
    body = _new_reply_text(_message_text(message))
    if not re.search(r"\b(unsubscribe|stop|remove|not\s+interested)\b", f"{subject}\n{body}", re.IGNORECASE):
        return None

    add_suppressed_recipient(sender, "imap_reply")
    return sender


def poll_unsubscribe_replies() -> int:
    if not is_imap_configured():
        return 0

    processed_count = 0
    with imaplib.IMAP4_SSL(
        settings.IMAP_HOST,
        settings.IMAP_PORT,
        timeout=20,
    ) as mailbox:
        mailbox.login(settings.IMAP_USERNAME, settings.IMAP_PASSWORD)
        mailbox.select("INBOX")
        last_uid = get_last_imap_uid()
        status_code, search_data = mailbox.uid("search", None, "UID", f"{last_uid + 1}:*")
        if status_code != "OK":
            raise RuntimeError(f"IMAP search failed: {status_code}")

        message_ids = search_data[0].split() if search_data and search_data[0] else []
        for message_id in message_ids:
            status_code, message_data = mailbox.uid("fetch", message_id, "(RFC822)")
            if status_code != "OK":
                raise RuntimeError(f"IMAP could not fetch message {message_id.decode()}: {status_code}")

            raw_message = next(
                (part[1] for part in message_data if isinstance(part, tuple) and isinstance(part[1], bytes)),
                None,
            )
            if raw_message is None:
                raise RuntimeError(f"IMAP returned no message content for {message_id.decode()}.")

            recipient = process_unsubscribe_message(raw_message)
            if recipient is not None:
                status_code, _ = mailbox.uid("store", message_id, "+FLAGS", "\\Seen")
                if status_code != "OK":
                    raise RuntimeError(f"IMAP could not mark processed reply as read: {message_id.decode()}")
                processed_count += 1
                logger.info("Processed unsubscribe reply from %s", recipient)
            save_last_imap_uid(int(message_id))

    return processed_count
