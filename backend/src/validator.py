import re
from typing import List, Tuple

SPAM_PHRASES = [
    "free money",
    "100% guaranteed",
    "100% guarantee",
    "make money fast",
    "risk-free",
    "risk free",
    "double your income",
    "act now",
    "earn cash",
    "no cost",
    "click here",
    "get rich",
    "guaranteed results",
    "miracle",
    "pure profit",
]

# Service keyword detectors
SERVICE_PATTERNS = {
    "web design": [
        re.compile(r"\bweb\s+design\b", re.IGNORECASE),
    ],
    "SEO": [
        re.compile(r"\bseo\b", re.IGNORECASE),
        re.compile(r"\bsearch\s+engine\s+optimization\b", re.IGNORECASE),
    ],
    "website redesign": [
        re.compile(r"\bwebsite\s+redesign\b", re.IGNORECASE),
        re.compile(r"\bredesign\b", re.IGNORECASE),
    ],
}

FORBIDDEN_CALL_PATTERNS = [
    re.compile(r"\b(phone\s+call|quick\s+call|brief\s+call|schedule\s+a\s+call|hop\s+on\s+a\s+call|book\s+a\s+call|jump\s+on\s+a\s+call|introductory\s+call|10-minute|15-minute|ten-minute|fifteen-minute|set\s+up\s+a\s+call|open\s+to\s+a\s+call|for\s+a\s+call|on\s+a\s+call|call\s+this\s+week|call\s+this\s+thursday|call\s+with\s+me)\b", re.IGNORECASE),
    re.compile(r"\b(can\s+we\s+call|would\s+you\s+be\s+open\s+to\s+a\s+call|hop\s+on\s+zoom|schedule\s+a\s+zoom|hop\s+on\s+a\s+quick\s+call)\b", re.IGNORECASE),
]

def clean_email_text(text: str) -> str:
    """Strips markdown code blocks, quotes, or accidental formatting added by AI."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()
    # Strip any enclosing quotation marks
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def validate_email_body(text: str, service: str) -> Tuple[bool, List[str], str]:
    """
    Validates email body against strict rules.
    Returns: (is_valid: bool, error_messages: list[str], cleaned_text: str)
    """
    cleaned = clean_email_text(text)
    errors: List[str] = []

    if not cleaned:
        return False, ["Email body is completely empty."], cleaned

    # 1. Must start with "Hello"
    if not re.match(r"^Hello\b", cleaned, re.IGNORECASE):
        errors.append("Email must start with the greeting 'Hello'.")

    # 2. Length must be short and concise (between 45 and 95 words)
    words = cleaned.split()
    word_count = len(words)
    if word_count < 45:
        errors.append(f"Email is too short: {word_count} words (must be between 45 and 95 words).")
    elif word_count > 95:
        errors.append(f"Email is too long: {word_count} words (must be between 45 and 95 words). Please keep it short and professional.")

    # 3. No placeholders such as [Name] or {company}
    placeholder_matches = re.findall(r"\[[^\]]+\]|\{[^\}]+\}|<[a-zA-Z0-9_\-\s]+>", cleaned)
    if placeholder_matches:
        errors.append(f"Email contains forbidden placeholders: {', '.join(set(placeholder_matches))}.")

    # 4. No links (URLs, http, https, www, domain names)
    link_match = re.search(r"https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.(?:com|org|net|io|co|ai|app|dev)\b", cleaned, re.IGNORECASE)
    if link_match:
        errors.append(f"Email contains links or URLs ({link_match.group(0)}), which are strictly forbidden.")

    # 5. Selected service must be clearly mentioned
    current_patterns = SERVICE_PATTERNS.get(service, [])
    has_current_service = any(p.search(cleaned) for p in current_patterns)
    if not has_current_service:
        errors.append(f"The selected service '{service}' is not clearly mentioned in the email body.")

    # 6. Other services must not be mentioned
    for other_service, patterns in SERVICE_PATTERNS.items():
        if other_service.lower() != service.lower():
            for p in patterns:
                m = p.search(cleaned)
                if m:
                    errors.append(f"Forbidden mention of another service '{other_service}' ('{m.group(0)}') found inside a {service} email.")
                    break

    # 7. No spam phrases
    lower_text = cleaned.lower()
    for phrase in SPAM_PHRASES:
        if phrase in lower_text:
            errors.append(f"Spam phrase detected: '{phrase}'. Must not be used.")

    # 8. Do not ask for phone calls or meetings
    for cp in FORBIDDEN_CALL_PATTERNS:
        cm = cp.search(cleaned)
        if cm:
            errors.append(f"Do not ask for a phone call or meeting ('{cm.group(0)}'). Instead, end by asking the recipient to reply to this email if they agree or are interested.")
            break

    # 9. Call to action must ask to reply
    if not re.search(r"\breply\b", cleaned, re.IGNORECASE):
        errors.append("Email must end with a low-friction call to action asking the recipient to reply to this email if they agree or are interested.")

    return len(errors) == 0, errors, cleaned
