from typing import List, Optional
from pydantic import BaseModel, Field

BUSINESS_TYPES = [
    "restaurant",
    "real estate",
    "clinic or hospital",
    "online store",
    "school or academy",
    "other business"
]

SERVICES = [
    "web design",
    "SEO",
    "website redesign"
]

SERVICE_SUBJECTS = {
    "web design": "Quick question regarding your website",
    "SEO": "Quick question about your website on Google",
    "website redesign": "Quick thought regarding your website"
}

def get_service_subject(business_type: str, service: str) -> str:
    type_labels = {
        "restaurant": "restaurant website",
        "real estate": "property website",
        "clinic or hospital": "clinic website",
        "online store": "online store",
        "school or academy": "school website",
        "other business": "website",
    }
    label = type_labels.get(business_type, "website")
    if service == "SEO":
        return f"Quick question about your {label} on Google"
    elif service == "website redesign":
        return f"Quick thought regarding your {label}"
    else:
        return f"Quick question regarding your {label}"

class CampaignCreateRequest(BaseModel):
    business_type: str = Field(..., description="Business type (restaurant, real estate, etc.)")
    service: str = Field(..., description="Service (web design, SEO, website redesign)")
    email_addresses: List[str] = Field(..., description="List of recipient email addresses")

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=1024)

class CampaignResponse(BaseModel):
    id: int
    business_type: str
    service: str
    total_emails: int
    created_time: str
    sent_count: int = 0
    waiting_count: int = 0
    sending_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    unsubscribed_count: int = 0
    progress_percentage: float = 0.0

class EmailDetail(BaseModel):
    id: int
    campaign_id: int
    recipient: str
    business_type: str
    service: str
    subject: str
    body: Optional[str] = None
    status: str
    error_reason: Optional[str] = None
    attempts: int = 0
    sent_time: Optional[str] = None
    created_time: str

class StatsResponse(BaseModel):
    sent: int
    waiting: int
    not_sent: int
    blocked_by_checks: int
    unsubscribed: int
    sent_last_24h: int
    daily_limit: int

class RetryResponse(BaseModel):
    retried_count: int
    message: str
