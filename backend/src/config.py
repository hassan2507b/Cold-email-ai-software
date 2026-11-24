import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    # Database
    DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "coldmail.db"))

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # SMTP Settings (Gmail)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Sender Branding
    SENDER_NAME: str = os.getenv("SENDER_NAME", "Alex Carter")
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "Apex Digital Solutions")

    # Queue & Rate Limits
    EMAIL_DELAY_SECONDS: float = float(os.getenv("EMAIL_DELAY_SECONDS", "0"))
    DAILY_EMAIL_LIMIT: int = int(os.getenv("DAILY_EMAIL_LIMIT", "400"))

    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Dashboard authentication
    APP_USERNAME: str = os.getenv("APP_USERNAME", "")
    APP_PASSWORD: str = os.getenv("APP_PASSWORD", "")
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")
    SESSION_DURATION_SECONDS: int = int(os.getenv("SESSION_DURATION_SECONDS", "43200"))

    # IMAP unsubscribe monitoring
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USERNAME: str = os.getenv("IMAP_USERNAME", "")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "")
    IMAP_POLL_INTERVAL_SECONDS: int = int(os.getenv("IMAP_POLL_INTERVAL_SECONDS", "60"))

settings = Settings()
