import pytest
import sqlite3
import os
from email.message import EmailMessage
from fastapi.testclient import TestClient

# Ensure test DB is used
os.environ["DB_PATH"] = "test_coldmail.db"

from backend.src.main import app, clean_and_validate_emails
from backend.src.database import init_db, get_db, count_sent_last_24_hours
from backend.src.validator import validate_email_body, clean_email_text
from backend.src.prompts import build_initial_prompt, build_fix_prompt
from backend.src.email_sender import append_system_signature
from backend.src.config import settings
from backend.src.database import add_suppressed_recipient, claim_next_waiting_email
from backend.src.imap_monitor import process_unsubscribe_message

client = TestClient(app, headers={"X-Requested-With": "ColdMailDashboard"})

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    settings.APP_USERNAME = "test-admin"
    settings.APP_PASSWORD = "test-password-long-enough"
    settings.SESSION_SECRET = "test-session-secret-that-is-long-enough-123456"
    client.cookies.clear()
    init_db()
    login_response = client.post(
        "/api/auth/login",
        json={"username": settings.APP_USERNAME, "password": settings.APP_PASSWORD},
    )
    assert login_response.status_code == 200
    yield
    # Cleanup test DB if needed
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM emails")
            conn.execute("DELETE FROM campaigns")
            conn.execute("DELETE FROM suppressed_recipients")
            conn.execute("DELETE FROM imap_state")
    except Exception:
        pass
    client.cookies.clear()

def test_authentication_required():
    client.cookies.clear()
    response = client.get("/api/campaigns")
    assert response.status_code == 401
    login_response = client.post(
        "/api/auth/login",
        json={"username": settings.APP_USERNAME, "password": settings.APP_PASSWORD},
    )
    assert login_response.status_code == 200
    assert client.get("/api/auth/session").status_code == 200
    protected_write = client.post(
        "/api/emails/retry-problems",
        headers={"X-Requested-With": "invalid"},
    )
    assert protected_write.status_code == 403

def test_open_dashboard_when_auth_disabled():
    old_user = settings.APP_USERNAME
    old_pass = settings.APP_PASSWORD
    try:
        settings.APP_USERNAME = ""
        settings.APP_PASSWORD = ""
        client.cookies.clear()
        response = client.get("/api/campaigns")
        assert response.status_code == 200
    finally:
        settings.APP_USERNAME = old_user
        settings.APP_PASSWORD = old_pass

def test_campaign_skips_unsubscribed_recipients():
    add_suppressed_recipient("opted-out@example.com", "imap_reply")
    response = client.post("/api/campaigns", json={
        "business_type": "restaurant",
        "service": "web design",
        "email_addresses": ["opted-out@example.com", "new@example.com"],
    })
    assert response.status_code == 201
    assert response.json()["unsubscribed_count"] == 1
    assert response.json()["waiting_count"] == 1
    with get_db() as conn:
        row = conn.execute(
            "SELECT status FROM emails WHERE recipient = 'opted-out@example.com'"
        ).fetchone()
    assert row["status"] == "unsubscribed"

def test_imap_unsubscribe_reply_is_suppressed():
    with get_db() as conn:
        conn.execute("""
            INSERT INTO campaigns (id, business_type, service, total_emails, created_time)
            VALUES (102, 'restaurant', 'web design', 1, '2026-10-29T00:00:00')
        """)
        conn.execute("""
            INSERT INTO emails (campaign_id, recipient, business_type, service, subject, status, created_time)
            VALUES (102, 'person@example.com', 'restaurant', 'web design', 'Web Design Offer', 'waiting', '2026-10-29T00:00:00')
        """)
    message = EmailMessage()
    message["From"] = "Prospect <person@example.com>"
    message["Subject"] = "Re: Your website"
    message.set_content("Please unsubscribe me from future emails.")
    assert process_unsubscribe_message(message.as_bytes()) == "person@example.com"
    with get_db() as conn:
        row = conn.execute(
            "SELECT source FROM suppressed_recipients WHERE recipient = 'person@example.com'"
        ).fetchone()
        email_row = conn.execute(
            "SELECT status FROM emails WHERE recipient = 'person@example.com'"
        ).fetchone()
    assert row["source"] == "imap_reply"
    assert email_row["status"] == "unsubscribed"

def test_imap_poller_processes_new_replies_and_persists_cursor(monkeypatch):
    message = EmailMessage()
    message["From"] = "person@example.com"
    message["Subject"] = "Re: Your website"
    message.set_content("unsubscribe")
    raw_message = message.as_bytes()

    class FakeMailbox:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def login(self, _username, _password):
            return "OK", []

        def select(self, _folder):
            return "OK", []

        def uid(self, command, *args):
            if command == "search":
                assert args == (None, "UID", "1:*")
                return "OK", [b"1"]
            if command == "fetch":
                return "OK", [(b"1 (RFC822)", raw_message)]
            if command == "store":
                return "OK", []
            raise AssertionError(f"Unexpected IMAP command: {command}")

    monkeypatch.setattr(settings, "IMAP_USERNAME", "imap-user@example.com")
    monkeypatch.setattr(settings, "IMAP_PASSWORD", "imap-password")
    monkeypatch.setattr("backend.src.imap_monitor.imaplib.IMAP4_SSL", lambda *args, **kwargs: FakeMailbox())
    from backend.src.imap_monitor import poll_unsubscribe_replies

    assert poll_unsubscribe_replies() == 1
    with get_db() as conn:
        row = conn.execute(
            "SELECT state_value FROM imap_state WHERE state_key = 'last_uid'"
        ).fetchone()
    assert row["state_value"] == "1"

def test_imap_quoted_unsubscribe_line_does_not_opt_out_sender():
    message = EmailMessage()
    message["From"] = "person@example.com"
    message["Subject"] = "Re: Your website"
    message.set_content(
        "Thanks for your message.\n\n"
        "On Monday, sales@example.com wrote:\n"
        "> To unsubscribe from future emails, reply with 'unsubscribe'."
    )
    assert process_unsubscribe_message(message.as_bytes()) is None
    with get_db() as conn:
        row = conn.execute(
            "SELECT recipient FROM suppressed_recipients WHERE recipient = 'person@example.com'"
        ).fetchone()
    assert row is None

def test_latest_emails_limit_is_bounded():
    assert client.get("/api/reports/latest-emails?limit=101").status_code == 422

def test_worker_claim_is_atomic_and_respects_daily_limit():
    with get_db() as conn:
        conn.execute("""
            INSERT INTO campaigns (id, business_type, service, total_emails, created_time)
            VALUES (101, 'restaurant', 'web design', 1, '2026-10-29T00:00:00')
        """)
        conn.execute("""
            INSERT INTO emails (campaign_id, recipient, business_type, service, subject, status, created_time)
            VALUES (101, 'queued@example.com', 'restaurant', 'web design', 'Web Design Offer', 'waiting', '2026-10-29T00:00:00')
        """)
    claimed = claim_next_waiting_email(1)
    assert claimed and claimed["recipient"] == "queued@example.com"
    assert claim_next_waiting_email(1) is None

def test_clean_and_validate_emails():
    raw_list = [
        "john@example.com",
        "  JOHN@example.com ",  # Duplicate with different case & space
        "invalid-email-address",
        "sarah.connor@domain.org, mike@agency.io",  # Comma separated
        "notanemail",
        "sarah.connor@domain.org"  # Duplicate
    ]
    valid, dups, invalid = clean_and_validate_emails(raw_list)
    assert len(valid) == 3
    assert "john@example.com" in valid
    assert "sarah.connor@domain.org" in valid
    assert "mike@agency.io" in valid
    assert dups == 2
    assert invalid == 2

def test_validator_rules():
    # Valid web design email (short, professional, ends with reply CTA)
    valid_text = (
        "Hello,\n"
        "Many restaurants lose high commission percentages to third-party delivery apps because "
        "their online food menu is difficult to navigate on mobile devices.\n"
        "Our specialized web design team creates clean, responsive websites tailored to turn "
        "visitors into direct paying customers and drive effortless table reservations.\n"
        "If you agree this could help, simply reply to this email and let me know."
    )
    is_val, errs, cleaned = validate_email_body(valid_text, "web design")
    assert is_val is True
    assert len(errs) == 0

    # Test missing "Hello"
    text_no_hello = valid_text.replace("Hello,", "Hi there,")
    is_val, errs, _ = validate_email_body(text_no_hello, "web design")
    assert is_val is False
    assert any("must start with the greeting" in e.lower() for e in errs)

    # Test short length
    short_text = "Hello, we do web design. Please reply."
    is_val, errs, _ = validate_email_body(short_text, "web design")
    assert is_val is False
    assert any("too short" in e.lower() for e in errs)

    # Test forbidden placeholder
    ph_text = valid_text.replace("restaurants", "[BusinessName]")
    is_val, errs, _ = validate_email_body(ph_text, "web design")
    assert is_val is False
    assert any("placeholders" in e.lower() for e in errs)

    # Test link presence
    link_text = valid_text + " Visit https://mysite.com"
    is_val, errs, _ = validate_email_body(link_text, "web design")
    assert is_val is False
    assert any("links or urls" in e.lower() for e in errs)

    # Test cross-service forbidden mention (e.g. SEO inside web design)
    cross_text = valid_text + " We also provide comprehensive SEO ranking packages."
    is_val, errs, _ = validate_email_body(cross_text, "web design")
    assert is_val is False
    assert any("forbidden mention of another service" in e.lower() for e in errs)

    # Test spam phrase
    spam_text = valid_text + " We promise 100% guaranteed success."
    is_val, errs, _ = validate_email_body(spam_text, "web design")
    assert is_val is False
    assert any("spam phrase detected" in e.lower() for e in errs)

def test_validator_enforces_45_to_95_word_bounds():
    def body_with_word_count(count):
        middle_count = count - 4
        return "Hello " + " ".join(["word"] * middle_count) + " web design reply"

    assert validate_email_body(body_with_word_count(45), "web design")[0]
    assert validate_email_body(body_with_word_count(95), "web design")[0]
    assert not validate_email_body(body_with_word_count(44), "web design")[0]
    assert not validate_email_body(body_with_word_count(96), "web design")[0]

def test_validator_forbids_calls_and_requires_reply():
    call_email = (
        "Hello,\n"
        "Many restaurants struggle with mobile ordering and lose high commission fees to delivery apps.\n"
        "Our web design team builds responsive websites to turn visitors into direct paying customers.\n"
        "Would you be open to a quick 10-minute call this Thursday to discuss?"
    )
    is_val, errs, _ = validate_email_body(call_email, "web design")
    assert is_val is False
    assert any("do not ask for a phone call" in e.lower() for e in errs)

def test_signature_appending():
    body = "Hello,\n\nThis is a sample cold email body."
    signed = append_system_signature(body)
    assert "Best regards," in signed
    assert "unsubscribe" in signed

def test_campaign_create_api():
    payload = {
        "business_type": "restaurant",
        "service": "web design",
        "email_addresses": [
            "manager1@bistro.com",
            "manager2@cafe.com",
            "manager1@bistro.com",  # Duplicate
            "bad-address"
        ]
    }
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["total_emails"] == 2
    assert data["business_type"] == "restaurant"
    assert data["service"] == "web design"

def test_reports_stats_api():
    response = client.get("/api/reports/stats")
    assert response.status_code == 200
    data = response.json()
    assert "sent" in data
    assert "waiting" in data
    assert "not_sent" in data
    assert "blocked_by_checks" in data
    assert "sent_last_24h" in data
    assert data["daily_limit"] == 400

def test_retry_problems_api():
    # Insert a failed email and a blocked email
    with get_db() as conn:
        conn.execute("""
            INSERT INTO campaigns (id, business_type, service, total_emails, created_time)
            VALUES (99, 'restaurant', 'web design', 2, '2026-10-29T00:00:00')
        """)
        conn.execute("""
            INSERT INTO emails (campaign_id, recipient, business_type, service, subject, status, error_reason, attempts, created_time)
            VALUES (99, 'fail@example.com', 'restaurant', 'web design', 'Web Design Offer', 'failed', 'SMTP Error', 1, '2026-10-29T00:00:00')
        """)
        conn.execute("""
            INSERT INTO emails (campaign_id, recipient, business_type, service, subject, status, error_reason, attempts, created_time)
            VALUES (99, 'blocked@example.com', 'restaurant', 'web design', 'Web Design Offer', 'blocked by checks', 'Link found', 3, '2026-10-29T00:00:00')
        """)

    response = client.post("/api/emails/retry-problems")
    assert response.status_code == 200
    data = response.json()
    assert data["retried_count"] >= 2

    # Verify they are now waiting
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, error_reason, attempts FROM emails WHERE id IN (SELECT id FROM emails WHERE campaign_id = 99)")
        rows = cursor.fetchall()
        for r in rows:
            assert r["status"] == "waiting"
            assert r["error_reason"] is None
            assert r["attempts"] == 0
