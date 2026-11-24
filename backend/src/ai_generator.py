import logging
from typing import Tuple, List, Optional
import httpx
from .config import settings
from .prompts import build_initial_prompt, build_fix_prompt
from .validator import validate_email_body

logger = logging.getLogger(__name__)

FAST_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

class EmailGenerator:
    def __init__(self):
        self._http_client = httpx.Client(
            timeout=12.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def _call_gemini_model(self, model_name: str, api_key: str, prompt: str) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.6,
                "topP": 0.9,
                "maxOutputTokens": 250,
            }
        }
        resp = self._http_client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        else:
            logger.warning(f"Gemini model '{model_name}' returned status {resp.status_code}: {resp.text[:150]}")
            return None

    def _call_gemini(self, prompt: str) -> str:
        """Invokes Gemini using ultra-fast keep-alive HTTP with model fallback."""
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in backend/.env. Please provide a valid Gemini API key.")

        configured_model = settings.GEMINI_MODEL.strip() or "gemini-3.5-flash-lite"
        # Models in priority order: configured first, then ultra-fast alternatives
        models_to_try = [configured_model] + [m for m in FAST_MODELS if m != configured_model]

        last_error = None
        for model_name in models_to_try:
            try:
                text = self._call_gemini_model(model_name, api_key, prompt)
                if text:
                    return text
            except Exception as e:
                last_error = e
                logger.warning(f"Call with model '{model_name}' failed: {e}. Trying next...")

        # If direct keep-alive calls failed, try google-genai SDK as last-ditch fallback
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=configured_model,
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e

        raise ValueError(f"All Gemini generation attempts failed. Last error: {last_error}")

    def generate_and_validate(self, business_type: str, service: str) -> Tuple[bool, str, List[str], int]:
        """
        Generates cold email body and validates it up to 3 tries.
        Returns:
            (is_valid: bool, final_body: str, error_reasons: list[str], total_attempts: int)
        """
        attempt = 1
        max_attempts = 3

        prompt = build_initial_prompt(business_type, service)
        raw_text = self._call_gemini(prompt)
        is_valid, errors, cleaned = validate_email_body(raw_text, service)

        while not is_valid and attempt < max_attempts:
            attempt += 1
            logger.info(f"Email failed validation on attempt {attempt - 1}. Fixing with errors: {errors}")
            fix_prompt = build_fix_prompt(cleaned, errors, business_type, service)
            raw_text = self._call_gemini(fix_prompt)
            is_valid, errors, cleaned = validate_email_body(raw_text, service)

        return is_valid, cleaned, errors, attempt

email_generator = EmailGenerator()
