import time
import threading
import logging
from datetime import datetime, timezone
from .config import settings
from .database import get_db, claim_next_waiting_email
from .ai_generator import email_generator
from .email_sender import send_smtp_email, append_system_signature
from .imap_monitor import is_imap_configured, poll_unsubscribe_replies

logger = logging.getLogger(__name__)

class EmailQueueWorker:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._imap_thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.info("Email queue worker is already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ColdEmailWorker")
        self._thread.start()
        if is_imap_configured():
            self._imap_thread = threading.Thread(
                target=self._run_imap_monitor,
                daemon=True,
                name="ColdEmailImapMonitor",
            )
            self._imap_thread.start()
        else:
            logger.warning("IMAP unsubscribe monitoring is disabled; configure IMAP_USERNAME and IMAP_PASSWORD.")
        logger.info("Background cold email worker thread started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._imap_thread:
            self._imap_thread.join(timeout=25)
        logger.info("Cold email worker stopped.")

    def _run_imap_monitor(self):
        while not self._stop_event.is_set():
            try:
                processed = poll_unsubscribe_replies()
                if processed:
                    logger.info("Processed %s unsubscribe reply/replies.", processed)
            except Exception:
                logger.exception("IMAP unsubscribe polling failed; it will retry.")
            self._stop_event.wait(max(10, settings.IMAP_POLL_INTERVAL_SECONDS))

    def _run_loop(self):
        logger.info("Cold email worker loop initialized.")
        while not self._stop_event.is_set():
            try:
                email_row = claim_next_waiting_email(settings.DAILY_EMAIL_LIMIT)

                # If no email is waiting, wait briefly
                if not email_row:
                    time.sleep(2)
                    continue

                # 3. Process the email
                self._process_single_email(email_row)

                # 4. Optional delay between emails
                if settings.EMAIL_DELAY_SECONDS > 0:
                    time.sleep(settings.EMAIL_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Unexpected error in cold email worker loop: {e}", exc_info=True)
                time.sleep(3)

    def _process_single_email(self, email_data: dict):
        email_id = email_data["id"]
        recipient = email_data["recipient"]
        business_type = email_data["business_type"]
        service = email_data["service"]
        subject = email_data["subject"]

        logger.info(f"Processing email #{email_id} for {recipient} ({business_type} - {service})")

        # Step A: Generate email with Gemini AI and validate with Python rules
        try:
            is_valid, ai_body, errors, attempts = email_generator.generate_and_validate(business_type, service)
        except Exception as e:
            raw_err = str(e)
            if "getaddrinfo failed" in raw_err or "11001" in raw_err:
                error_msg = "Internet connection dropped ([Errno 11001] getaddrinfo failed). The system could not reach Google Gemini. Please check your internet connection and click 'Retry all problems' on the Report page."
            else:
                error_msg = f"AI Generation Failed: {raw_err}"
            logger.error(f"Email #{email_id} error: {error_msg}")
            with get_db() as conn:
                conn.execute("""
                    UPDATE emails
                    SET status = 'failed',
                        error_reason = ?,
                        attempts = attempts + 1,
                        claimed_time = NULL
                    WHERE id = ? AND status = 'sending'
                """, (error_msg, email_id))
            return

        # Step B: If validation checks failed after 3 attempts, mark as blocked by checks
        if not is_valid:
            error_reason = f"Blocked by Python checks: {'; '.join(errors)}"
            logger.warning(f"Email #{email_id} to {recipient} blocked: {error_reason}")
            with get_db() as conn:
                conn.execute("""
                    UPDATE emails
                    SET status = 'blocked by checks',
                        body = ?,
                        error_reason = ?,
                        attempts = ?,
                        claimed_time = NULL
                    WHERE id = ? AND status = 'sending'
                """, (ai_body, error_reason, attempts, email_id))
            return

        # Step C: Append system signature and unsubscribe line
        full_email_body = append_system_signature(ai_body)

        # Step D: Send email via Gmail SMTP
        try:
            with get_db() as conn:
                row = conn.execute("SELECT status FROM emails WHERE id = ?", (email_id,)).fetchone()
                if not row or row["status"] != "sending":
                    logger.info("Skipping email #%s because it is no longer queued for sending.", email_id)
                    return
            send_smtp_email(recipient=recipient, subject=subject, full_body=full_email_body)
            now_iso = datetime.now(timezone.utc).isoformat()
            with get_db() as conn:
                conn.execute("""
                    UPDATE emails
                    SET status = 'sent',
                        body = ?,
                        sent_time = ?,
                        error_reason = NULL,
                        attempts = ?,
                        claimed_time = NULL
                    WHERE id = ? AND status = 'sending'
                """, (full_email_body, now_iso, attempts, email_id))
            logger.info(f"Email #{email_id} to {recipient} successfully sent.")
        except Exception as e:
            err_str = f"SMTP Send Error: {str(e)}"
            logger.error(f"Email #{email_id} send failed: {err_str}")
            with get_db() as conn:
                conn.execute("""
                    UPDATE emails
                    SET status = 'failed',
                        body = ?,
                        error_reason = ?,
                        attempts = ?,
                        claimed_time = NULL
                    WHERE id = ? AND status = 'sending'
                """, (full_email_body, err_str, attempts, email_id))

worker = EmailQueueWorker()
