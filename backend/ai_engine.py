import base64
import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ISSUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["Road damage", "Garbage / sanitation", "Water leakage", "Drainage / sewage", "Streetlight", "Pollution", "Other", "Not enough visual evidence"],
        },
        "severity": {"type": "string", "enum": ["Low", "Medium", "High", "Critical", "Cannot assess"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "image_observation": {"type": "string"},
        "severity_reason": {"type": "string"},
        "recommended_department": {"type": "string"},
        "department_caveat": {"type": "string"},
        "complaint_title": {"type": "string"},
        "complaint_body": {"type": "string"},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "language": {"type": "string"},
    },
    "required": [
        "category", "severity", "confidence", "image_observation", "severity_reason",
        "recommended_department", "department_caveat", "complaint_title", "complaint_body",
        "missing_information", "language",
    ],
    "additionalProperties": False,
}


def _build_prompt(description: str, location: str, language: str) -> str:
    return f"""You are CivicPulse AI, an assistant that helps citizens prepare civic-infrastructure reports.
Analyze the attached image and the user-provided context. Return only the requested structured output.

User description: {description or 'No description supplied'}
User-provided location: {location or 'Not supplied'}
Requested complaint language: {language}

Rules:
- Classify only what is reasonably supported by the image and user text.
- Do not infer an exact address, date, cause, responsible authority, or official status from the image.
- The severity is a preliminary visual triage estimate, not an emergency-service assessment.
- Confidence describes confidence in the visual category, not confidence that a government agency is responsible.
- Recommend a broad likely department only (for example, local municipal body, public works/roads department, water utility, or pollution-control authority). Do not invent a named official, phone number, portal, or tracking ID.
- State in department_caveat that the responsible authority must be verified for the user's exact jurisdiction.
- If evidence is unclear, use 'Not enough visual evidence' or 'Cannot assess' and ask for more information in missing_information.
- Write the complaint in the requested language. Keep it factual, respectful, and do not add facts not supplied by the user or visible in the image.
- Do not claim the complaint has been submitted to any government office.
"""


def _call_gemini(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file and restart the server.")

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        input=[
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": mime_type,
            },
        ],
        response_format={"type": "text", "mime_type": "application/json", "schema": ISSUE_SCHEMA},
    )
    text = getattr(interaction, "output_text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response. Please retry with a clearer image.")
    return text


def analyze_civic_image(
    image_bytes: bytes,
    mime_type: str,
    description: str,
    location: str,
    language: str,
) -> dict[str, Any]:

    """Analyze a civic issue using Gemini multimodal AI."""

    prompt = _build_prompt(description, location, language)

    # Gemini is our only AI provider.
    raw = _call_gemini(image_bytes, mime_type, prompt)

    try:
        result = json.loads(raw)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid JSON. Please retry."
        ) from exc

    # Validate the AI response.
    required = ISSUE_SCHEMA["required"]

    missing = [
        field for field in required
        if field not in result
    ]

    if missing:
        raise RuntimeError(
            f"AI response is missing fields: {', '.join(missing)}"
        )

    result["provider"] = "gemini"

    return result
