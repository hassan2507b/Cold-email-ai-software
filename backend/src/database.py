import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from .config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Campaigns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_type TEXT NOT NULL,
                service TEXT NOT NULL,
                total_emails INTEGER NOT NULL,
                created_time TEXT NOT NULL
            )
        """)

        # Emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                recipient TEXT NOT NULL,
                business_type TEXT NOT NULL,
                service TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT,
                status TEXT NOT NULL, -- 'waiting', 'sending', 'sent', 'failed', 'blocked by checks'
                error_reason TEXT,
                attempts INTEGER DEFAULT 0,
                claimed_time TEXT,
                sent_time TEXT,
                created_time TEXT NOT NULL
            )
        """)

        email_columns = {
            row["name"] for row in cursor.execute("PRAGMA table_info(emails)").fetchall()
        }
        if "claimed_time" not in email_columns:
            cursor.execute("ALTER TABLE emails ADD COLUMN claimed_time TEXT")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppressed_recipients (
                recipient TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                created_time TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imap_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            )
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_campaign_id ON emails(campaign_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_recipient ON emails(recipient)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_sent_time ON emails(sent_time)")

        cursor.execute("""
            UPDATE emails
            SET status = 'waiting', claimed_time = NULL
            WHERE status = 'sending'
              AND (claimed_time IS NULL OR datetime(claimed_time) < datetime('now', '-5 minutes'))
              AND recipient NOT IN (SELECT recipient FROM suppressed_recipients)
        """)

        cursor.execute("""
            UPDATE emails
            SET status = 'unsubscribed',
                claimed_time = NULL,
                error_reason = 'Recipient unsubscribed from future emails.'
            WHERE recipient IN (SELECT recipient FROM suppressed_recipients)
              AND status IN ('waiting', 'failed', 'blocked by checks', 'sending')
        """)

def claim_next_waiting_email(daily_limit: int) -> dict | None:
    """Atomically claim the oldest waiting email across worker processes."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            UPDATE emails
            SET status = 'waiting', claimed_time = NULL
            WHERE status = 'sending'
              AND (claimed_time IS NULL OR datetime(claimed_time) < datetime('now', '-5 minutes'))
              AND recipient NOT IN (SELECT recipient FROM suppressed_recipients)
        """)
        active_count = conn.execute("""
            SELECT COUNT(*) AS count
            FROM emails
            WHERE status = 'sending'
               OR (
                    status = 'sent'
                    AND sent_time IS NOT NULL
                    AND datetime(sent_time) >= datetime('now', '-24 hours')
               )
        """).fetchone()["count"]
        if active_count >= daily_limit:
            return None

        conn.execute("""
            UPDATE emails
            SET status = 'unsubscribed',
                error_reason = 'Recipient unsubscribed from future emails.'
            WHERE status = 'waiting'
              AND recipient IN (SELECT recipient FROM suppressed_recipients)
        """)
        row = conn.execute("""
            SELECT id, campaign_id, recipient, business_type, service, subject, attempts
            FROM emails
            WHERE status = 'waiting'
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()
        if not row:
            return None

        updated = conn.execute(
            """
            UPDATE emails
            SET status = 'sending', claimed_time = datetime('now')
            WHERE id = ? AND status = 'waiting'
            """,
            (row["id"],),
        )
        if updated.rowcount != 1:
            return None
        return dict(row)

def add_suppressed_recipient(recipient: str, source: str) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO suppressed_recipients (recipient, source, created_time)
            VALUES (?, ?, ?)
            ON CONFLICT(recipient) DO NOTHING
        """, (recipient.lower(), source, now_iso))
        conn.execute("""
            UPDATE emails
            SET status = 'unsubscribed',
                claimed_time = NULL,
                error_reason = 'Recipient unsubscribed from future emails.'
            WHERE recipient = ?
              AND status IN ('waiting', 'failed', 'blocked by checks', 'sending')
        """, (recipient.lower(),))

def get_last_imap_uid() -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT state_value FROM imap_state WHERE state_key = 'last_uid'"
        ).fetchone()
        return int(row["state_value"]) if row else 0

def save_last_imap_uid(uid: int) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO imap_state (state_key, state_value)
            VALUES ('last_uid', ?)
            ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value
        """, (str(uid),))

def count_sent_last_24_hours() -> int:
    """Counts emails sent in the rolling last 24 hours."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM emails
            WHERE status = 'sent'
              AND sent_time IS NOT NULL
              AND datetime(sent_time) >= datetime('now', '-24 hours')
        """)
        row = cursor.fetchone()
        return row["count"] if row else 0
