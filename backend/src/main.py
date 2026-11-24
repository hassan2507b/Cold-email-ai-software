import re
import logging
import hmac
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    require_authenticated_session,
    validate_auth_settings,
)
from .config import settings
from .database import init_db, get_db, count_sent_last_24_hours
from .models import (
    CampaignCreateRequest,
    CampaignResponse,
    EmailDetail,
    LoginRequest,
    StatsResponse,
    RetryResponse,
    BUSINESS_TYPES,
    SERVICES,
    SERVICE_SUBJECTS,
    get_service_subject,
)
from .worker import worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("coldmail_backend")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def clean_and_validate_emails(raw_emails: List[str]) -> tuple[List[str], int, int]:
    """
    Parses, trims, validates, and deduplicates an input list of email strings.
    Returns: (valid_unique_emails, duplicates_count, invalid_count)
    """
    seen = set()
    valid_unique = []
    duplicates_count = 0
    invalid_count = 0

    for item in raw_emails:
        # Split on commas, semicolons, or newlines in case raw pasted blocks are provided
        chunks = re.split(r"[,;\n\r\t]+", str(item).strip())
        for chunk in chunks:
            email = chunk.strip().lower()
            if not email:
                continue
            if not EMAIL_REGEX.match(email):
                invalid_count += 1
                continue
            if email in seen:
                duplicates_count += 1
                continue
            seen.add(email)
            valid_unique.append(email)

    return valid_unique, duplicates_count, invalid_count

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_settings()
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting background cold email worker...")
    worker.start()
    yield
    logger.info("Shutting down background worker...")
    worker.stop()

app = FastAPI(
    title="AI Cold Email Sender API",
    description="Automated Cold Email Generator & Sender with Gemini AI & Pure Python Validation",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response):
    validate_auth_settings()
    if not (
        hmac.compare_digest(payload.username.encode("utf-8"), settings.APP_USERNAME.encode("utf-8"))
        and hmac.compare_digest(payload.password.encode("utf-8"), settings.APP_PASSWORD.encode("utf-8"))
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    secure_cookie = settings.FRONTEND_URL.lower().startswith("https://")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(payload.username),
        max_age=settings.SESSION_DURATION_SECONDS,
        httponly=True,
        secure=secure_cookie,
        samesite="none" if secure_cookie else "lax",
        path="/",
    )
    return {"authenticated": True}

@app.get("/api/auth/session", dependencies=[Depends(require_authenticated_session)])
def check_session():
    return {"authenticated": True}

@app.post("/api/auth/logout", dependencies=[Depends(require_authenticated_session)])
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.FRONTEND_URL.lower().startswith("https://"),
        httponly=True,
        samesite="none" if settings.FRONTEND_URL.lower().startswith("https://") else "lax",
    )
    return {"authenticated": False}

@app.post("/api/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreateRequest,
    _: None = Depends(require_authenticated_session),
):
    # Validate business type & service
    if payload.business_type not in BUSINESS_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid business type. Must be one of: {', '.join(BUSINESS_TYPES)}"
        )
    if payload.service not in SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service. Must be one of: {', '.join(SERVICES)}"
        )

    valid_emails, duplicates, invalid = clean_and_validate_emails(payload.email_addresses)
    if not valid_emails:
        raise HTTPException(
            status_code=400,
            detail=f"No valid email addresses found. Processed {duplicates} duplicate(s) and {invalid} invalid address(es)."
        )

    subject = get_service_subject(payload.business_type, payload.service)
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        suppressed = set()
        for start in range(0, len(valid_emails), 900):
            batch = valid_emails[start:start + 900]
            placeholders = ",".join("?" for _ in batch)
            rows = cursor.execute(
                f"SELECT recipient FROM suppressed_recipients WHERE recipient IN ({placeholders})",
                batch,
            ).fetchall()
            suppressed.update(row["recipient"] for row in rows)
        waiting_emails = [email for email in valid_emails if email not in suppressed]
        # 1. Insert campaign
        cursor.execute("""
            INSERT INTO campaigns (business_type, service, total_emails, created_time)
            VALUES (?, ?, ?, ?)
        """, (payload.business_type, payload.service, len(valid_emails), now_iso))
        campaign_id = cursor.lastrowid

        # 2. Insert queued and suppressed emails
        email_rows = [
            (
                campaign_id,
                email,
                payload.business_type,
                payload.service,
                subject,
                "unsubscribed" if email in suppressed else "waiting",
                "Recipient unsubscribed from future emails." if email in suppressed else None,
                now_iso,
            )
            for email in valid_emails
        ]
        cursor.executemany("""
            INSERT INTO emails (campaign_id, recipient, business_type, service, subject, status, error_reason, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, email_rows)

    logger.info(
        "Campaign #%s created with %s queued, %s unsubscribed, %s duplicate(s) removed, %s invalid discarded.",
        campaign_id,
        len(waiting_emails),
        len(suppressed),
        duplicates,
        invalid,
    )

    return CampaignResponse(
        id=campaign_id,
        business_type=payload.business_type,
        service=payload.service,
        total_emails=len(valid_emails),
        created_time=now_iso,
        waiting_count=len(waiting_emails),
        sending_count=0,
        sent_count=0,
        failed_count=0,
        blocked_count=0,
        unsubscribed_count=len(suppressed),
        progress_percentage=0.0
    )

@app.get("/api/campaigns", response_model=List[CampaignResponse], dependencies=[Depends(require_authenticated_session)])
def list_campaigns():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id, c.business_type, c.service, c.total_emails, c.created_time,
                COALESCE(SUM(CASE WHEN e.status = 'sent' THEN 1 ELSE 0 END), 0) AS sent_count,
                COALESCE(SUM(CASE WHEN e.status = 'waiting' THEN 1 ELSE 0 END), 0) AS waiting_count,
                COALESCE(SUM(CASE WHEN e.status = 'sending' THEN 1 ELSE 0 END), 0) AS sending_count,
                COALESCE(SUM(CASE WHEN e.status = 'failed' THEN 1 ELSE 0 END), 0) AS failed_count,
                COALESCE(SUM(CASE WHEN e.status = 'blocked by checks' THEN 1 ELSE 0 END), 0) AS blocked_count,
                COALESCE(SUM(CASE WHEN e.status = 'unsubscribed' THEN 1 ELSE 0 END), 0) AS unsubscribed_count
            FROM campaigns c
            LEFT JOIN emails e ON c.id = e.campaign_id
            GROUP BY c.id
            ORDER BY c.id DESC
        """)
        rows = cursor.fetchall()

    campaigns = []
    for r in rows:
        total = r["total_emails"]
        sent = r["sent_count"]
        progress = round((sent / total * 100), 1) if total > 0 else 0.0
        campaigns.append(CampaignResponse(
            id=r["id"],
            business_type=r["business_type"],
            service=r["service"],
            total_emails=total,
            created_time=r["created_time"],
            sent_count=sent,
            waiting_count=r["waiting_count"],
            sending_count=r["sending_count"],
            failed_count=r["failed_count"],
            blocked_count=r["blocked_count"],
            unsubscribed_count=r["unsubscribed_count"],
            progress_percentage=progress
        ))
    return campaigns

@app.get("/api/reports/stats", response_model=StatsResponse, dependencies=[Depends(require_authenticated_session)])
def get_reports_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END), 0) AS sent,
                COALESCE(SUM(CASE WHEN status = 'waiting' THEN 1 ELSE 0 END), 0) AS waiting,
                COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) AS not_sent,
                COALESCE(SUM(CASE WHEN status = 'blocked by checks' THEN 1 ELSE 0 END), 0) AS blocked_by_checks,
                COALESCE(SUM(CASE WHEN status = 'unsubscribed' THEN 1 ELSE 0 END), 0) AS unsubscribed
            FROM emails
        """)
        row = cursor.fetchone()

    sent_24h = count_sent_last_24_hours()

    return StatsResponse(
        sent=row["sent"] if row else 0,
        waiting=row["waiting"] if row else 0,
        not_sent=row["not_sent"] if row else 0,
        blocked_by_checks=row["blocked_by_checks"] if row else 0,
        unsubscribed=row["unsubscribed"] if row else 0,
        sent_last_24h=sent_24h,
        daily_limit=settings.DAILY_EMAIL_LIMIT
    )

@app.get(
    "/api/reports/latest-emails",
    response_model=List[EmailDetail],
    dependencies=[Depends(require_authenticated_session)],
)
def get_latest_emails(limit: int = Query(20, ge=1, le=100)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, campaign_id, recipient, business_type, service, subject, body, status, error_reason, attempts, sent_time, created_time
            FROM emails
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
    return [EmailDetail(**dict(r)) for r in rows]

@app.post(
    "/api/emails/retry-problems",
    response_model=RetryResponse,
    dependencies=[Depends(require_authenticated_session)],
)
def retry_all_problems():
    """Resets all 'failed' and 'blocked by checks' emails back to 'waiting'."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE emails
            SET status = 'waiting',
                error_reason = NULL,
                attempts = 0
            WHERE status IN ('failed', 'blocked by checks')
        """)
        retried_count = cursor.rowcount

    return RetryResponse(
        retried_count=retried_count,
        message=f"Successfully queued {retried_count} problem email(s) back into the sending queue."
    )

@app.get("/api/emails", response_model=List[EmailDetail], dependencies=[Depends(require_authenticated_session)])
def get_all_emails(
    search: Optional[str] = Query(None, description="Search recipient email address"),
    status: Optional[str] = Query(None, description="Filter by status (sent, waiting, failed, blocked by checks)"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = """
        SELECT id, campaign_id, recipient, business_type, service, subject, body, status, error_reason, attempts, sent_time, created_time
        FROM emails
        WHERE 1=1
    """
    params = []

    if search and search.strip():
        query += " AND recipient LIKE ?"
        params.append(f"%{search.strip().lower()}%")

    if status and status.strip() and status.strip().lower() != "all":
        query += " AND status = ?"
        params.append(status.strip().lower())

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [EmailDetail(**dict(r)) for r in rows]

@app.get("/api/emails/{email_id}", response_model=EmailDetail, dependencies=[Depends(require_authenticated_session)])
def get_email_by_id(email_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, campaign_id, recipient, business_type, service, subject, body, status, error_reason, attempts, sent_time, created_time
            FROM emails
            WHERE id = ?
        """, (email_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Email record not found.")

    return EmailDetail(**dict(row))
