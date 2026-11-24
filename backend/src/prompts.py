"""Prompts and industry context configurations for Gemini cold email generation."""

BUSINESS_PAIN_POINTS = {
    "restaurant": (
        "many customers browse food menus from their phones, but if the menu is slow or hard to read, they end up ordering through third-party apps instead of directly"
    ),
    "real estate": (
        "prospective property buyers often leave if listing photos load slowly or pages feel hard to navigate on mobile devices"
    ),
    "clinic or hospital": (
        "patients frequently struggle to book consultations online or find doctor schedules easily on mobile phones"
    ),
    "online store": (
        "customers often abandon carts when checkout steps feel sluggish or product pages look cluttered on mobile"
    ),
    "school or academy": (
        "parents and students often struggle to locate course schedules or admission info on smartphones"
    ),
    "other business": (
        "potential clients frequently choose competitors if a business site loads slowly or looks outdated on mobile"
    ),
}

SERVICE_OFFERS = {
    "web design": (
        "I build modern, fast-loading web design solutions that make it simple for visitors to browse your services and reach out directly from their smartphones."
    ),
    "SEO": (
        "I help local businesses improve their SEO ranking on Google search so nearby customers can easily discover you when searching online."
    ),
    "website redesign": (
        "I help businesses with a modern website redesign to refresh the layout, make it mobile-friendly, and improve visitor inquiries."
    ),
}

# Names of services to detect accidental cross-service mentions
ALL_SERVICES = ["web design", "SEO", "website redesign"]

def build_initial_prompt(business_type: str, service: str) -> str:
    pain_points = BUSINESS_PAIN_POINTS.get(business_type, BUSINESS_PAIN_POINTS["other business"])
    offer_text = SERVICE_OFFERS.get(service, SERVICE_OFFERS["web design"])

    other_services = [s for s in ALL_SERVICES if s.lower() != service.lower()]
    forbidden_services_str = ", ".join(f'"{s}"' for s in other_services)

    return f"""You are a helpful consultant writing a brief, polite, 1-to-1 personal cold email to a {business_type}.
Write a very short, crisp, highly professional email reaching out to them.

Target Industry Context:
- Target Business: {business_type}
- Their Pain Point: {pain_points}
- Our Service: {offer_text}

STRICT REQUIREMENTS (Failure to follow will invalidate the email):
1. Write ONLY the email body. Do not include a subject line, header, signature, or sign-off.
2. Must start with exactly: "Hello,"
3. LENGTH: Must be very SHORT and concise — strictly between 50 and 80 words (2 to 3 brief sentences/paragraphs max). Absolutely NO long essays or walls of text.
4. TONE: Warm, helpful, polite, and natural conversational English (like one professional writing to another). Absolutely NO corporate jargon, no marketing hype (e.g. do not say "commission-free", "paying customers", "high-converting", or "game changer").
5. Focus EXCLUSIVELY on our "{service}" service. Clearly mention "{service}".
6. FORBIDDEN SERVICES: Strictly do NOT mention {forbidden_services_str}.
7. NO PLACEHOLDERS: Do not use placeholders like [Name], [Company], {{name}}, {{company}}, or any brackets. Write natural sentences that work without placeholders.
8. NO HYPERLINKS OR URLS: Do not include any web links or URLs.
9. NO SPAM WORDS: Never use marketing words like "special offer", "free", "discount", "risk free", "act now", "100% guaranteed", "profits", or "commission". Write naturally and sincerely.
10. CALL TO ACTION (CTA):
    - Do NOT ask for a phone call, Zoom, or meeting (do NOT say "call", "phone call", "schedule a call", or "10-minute call").
    - End by asking the recipient to simply REPLY to this email if they agree or are interested.
    Example endings:
    "If you agree this could help, simply reply to this email and let me know."
    "If this sounds interesting, just reply to this email and I will share a few quick examples."
    "If you agree, reply to this email and we can take it from there."
11. NO CLOSING SIGNATURE: Do not write "Best regards", sender name, or company. The system attaches the sender signature automatically.

Write only the short email body now:"""

def build_fix_prompt(original_text: str, errors: list[str], business_type: str, service: str) -> str:
    error_list_str = "\n".join(f"- {err}" for err in errors)
    other_services = [s for s in ALL_SERVICES if s.lower() != service.lower()]
    forbidden_services_str = ", ".join(f'"{s}"' for s in other_services)

    return f"""The cold email body you previously wrote failed validation checks. Please rewrite the email body to be short, crisp, and professional.

Target Business Type: {business_type}
Selected Service: {service}

VALIDATION ERRORS FOUND:
{error_list_str}

PREVIOUS FAILED TEXT:
\"\"\"{original_text}\"\"\"

MANDATORY RULES:
1. Fix all listed errors completely.
2. Must start with exactly: "Hello,"
3. Length MUST be strictly between 50 and 80 words (plain, concise English).
4. Clearly mention "{service}".
5. Strictly DO NOT mention {forbidden_services_str}.
6. ABSOLUTELY NO placeholders (no brackets [], no braces {{}}).
7. ABSOLUTELY NO links or URLs.
8. NO spam terms.
9. DO NOT ask for a phone call or meeting. End by asking the recipient to reply to this email if they agree or are interested.
10. Output ONLY the raw email body with NO signature, NO subject, and NO commentary.

Write the corrected short email body now:"""
