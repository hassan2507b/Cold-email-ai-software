import hashlib
import hmac
import logging
import time

from fastapi import HTTPException, Request, status

from .config import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "coldmail_session"


def is_auth_enabled() -> bool:
    """Authentication is only enabled if APP_USERNAME and APP_PASSWORD are set."""
    return bool(settings.APP_USERNAME and settings.APP_PASSWORD)


def validate_auth_settings() -> None:
    if not is_auth_enabled():
        logger.info("Dashboard authentication is disabled (open dashboard mode).")
        return
    if len(settings.APP_PASSWORD) < 8:
        raise RuntimeError("APP_PASSWORD must contain at least 8 characters.")
    if len(settings.SESSION_SECRET) < 16:
        raise RuntimeError("SESSION_SECRET must contain at least 16 characters.")
    if settings.SESSION_DURATION_SECONDS < 60:
        raise RuntimeError("SESSION_DURATION_SECONDS must be at least 60.")


def create_session_token(username: str) -> str:
    validate_auth_settings()
    expires_at = int(time.time()) + settings.SESSION_DURATION_SECONDS
    payload = f"{username}:{expires_at}"
    secret = settings.SESSION_SECRET or "default_coldmail_secret_key_12345678"
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def is_valid_session(token: str | None) -> bool:
    if not is_auth_enabled():
        return True
    if not token:
        return False
    try:
        username, expires_at_text, signature = token.rsplit(":", 2)
        expires_at = int(expires_at_text)
    except (ValueError, TypeError):
        return False

    payload = f"{username}:{expires_at_text}"
    secret = settings.SESSION_SECRET or "default_coldmail_secret_key_12345678"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        hmac.compare_digest(username.encode("utf-8"), settings.APP_USERNAME.encode("utf-8"))
        and hmac.compare_digest(signature, expected_signature)
        and expires_at > int(time.time())
    )


def require_authenticated_session(request: Request) -> None:
    # If auth is not configured, allow access directly (Rule 11: Do not require login by default)
    if not is_auth_enabled():
        return

    if not is_valid_session(request.cookies.get(SESSION_COOKIE_NAME)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
        )
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.headers.get("x-requested-with") != "ColdMailDashboard":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing request protection header.",
            )
