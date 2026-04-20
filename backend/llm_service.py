# Google AI Services Integration
# Model: gemini-2.0-flash via Google AI Studio
# Endpoint: generativelanguage.googleapis.com/v1beta
# Usage: Real-time crowd state reasoning and nudge generation
# Deployment: Google Cloud Run (asia-south1)

"""
CrowdSense AI — LLM Service
Wraps Google Gemini API for nudge generation, chat, and per-zone staff actions.
All calls have try/except with hard-coded fallback responses.
"""

import json
import logging
from typing import Any

import httpx
from dotenv import load_dotenv

import config

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level persistent async client
_client = httpx.AsyncClient(timeout=15)

# Startup validation
if not config.GEMINI_API_KEY:
    logger.warning("[llm_service] WARNING: GEMINI_API_KEY is not set in environment")

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

async def _call_gemini(system: str, user: str, max_tokens: int = 512) -> str:
    """Send a single-turn message to Gemini and return the text response."""
    if not config.GEMINI_API_KEY:
        logger.error("[llm_service] ERROR: GEMINI_API_KEY is missing from environment.")
        raise ValueError("Missing GEMINI_API_KEY")

    headers = {
        "content-type": "application/json",
    }
    url = f"{config.GEMINI_ENDPOINT}?key={config.GEMINI_API_KEY}"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    resp = await _client.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        logger.error(f"[llm_service] Gemini Error ({resp.status_code}): {resp.text}")
        resp.raise_for_status()
        
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Nudge generation
# ---------------------------------------------------------------------------

NUDGE_SYSTEM_PROMPT = (
    "You are CrowdSense, an AI crowd intelligence system for a large sports stadium. "
    "You receive real-time crowd density data across 14 zones. "
    "Your job: generate 2-3 short, specific, actionable nudges for attendees RIGHT NOW. "
    "Rules: each nudge must reference a SPECIFIC zone by name. "
    "Each nudge must state a concrete benefit (saves X minutes, less crowded). "
    "Tone: friendly, direct, never preachy. "
    "Only nudge when density difference between zones justifies it (>25 point gap). "
    "urgency: low <50 density, medium 50-75, high >75. "
    "Respond ONLY with valid JSON. No explanation, no markdown. "
    'Format: [{"zone": "Zone Name", "message": "Your nudge text here.", "urgency": "medium"}]'
)

_NUDGE_FALLBACK = [
    {
        "zone":    "Concession 2",
        "message": "Concession 2 is currently quieter — grab your snacks now and skip the rush!",
        "urgency": "low",
    },
    {
        "zone":    "Restroom West",
        "message": "Restroom West has shorter queues right now. Save 5+ minutes versus North.",
        "urgency": "low",
    },
]


async def generate_nudges(crowd_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate 2-3 attendee nudges grounded in live crowd data.
    
    Returns a list of {zone, message, urgency} dicts.
    Falls back to a static response on any error.
    """
    try:
        zones_summary = [
            {
                "name":    z["name"],
                "type":    z["type"],
                "density": z["density"],
                "wait":    z["wait_minutes"],
                "trend":   z["trend"],
            }
            for z in crowd_state.get("zones", [])
        ]
        user_msg = (
            f"Current event: {crowd_state.get('event', 'UNKNOWN')}.\n"
            f"Zone data:\n{json.dumps(zones_summary, indent=2)}"
        )
        raw = await _call_gemini(NUDGE_SYSTEM_PROMPT, user_msg, max_tokens=600)

        # Strip markdown fences if model adds them despite instructions
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        nudges = json.loads(raw)

        # Validate structure
        valid: list[dict] = []
        for item in nudges:
            if isinstance(item, dict) and "zone" in item and "message" in item:
                item.setdefault("urgency", "low")
                valid.append(item)
        return valid if valid else _NUDGE_FALLBACK

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[llm_service] generate_nudges error: {exc}")
        return _NUDGE_FALLBACK


# ---------------------------------------------------------------------------
# Attendee chat
# ---------------------------------------------------------------------------

CHAT_SYSTEM_TEMPLATE = (
    "You are a helpful stadium assistant with access to live crowd data. "
    "Answer the attendee's question using ONLY the provided crowd state data. "
    "Be specific: quote actual zone names, wait times, and density levels. "
    "If you recommend a zone, explain WHY using the data. "
    "Keep answers under 3 sentences. "
    "Never make up data not in the context. "
    "Current crowd state: {crowd_json}"
)

_CHAT_FALLBACK = (
    "Please refer to the live stadium map for the most current wait times and zone densities."
)


async def chat_with_context(
    message: str,
    history: list[dict[str, str]],
    crowd_state: dict[str, Any],
) -> str:
    """Answer an attendee question grounded in live crowd data.
    
    Args:
        message: The attendee's question
        history: List of {role: 'user'|'assistant', content: str}
        crowd_state: Current crowd state from simulator
        
    Returns:
        Plain-text answer string. Falls back to static response on error.
    """
    try:
        crowd_json = json.dumps(
            {
                "event": crowd_state.get("event"),
                "zones": [
                    {
                        "name":         z["name"],
                        "type":         z["type"],
                        "density":      z["density"],
                        "wait_minutes": z["wait_minutes"],
                        "trend":        z["trend"],
                    }
                    for z in crowd_state.get("zones", [])
                ],
            },
            indent=2,
        )
        system = CHAT_SYSTEM_TEMPLATE.format(crowd_json=crowd_json)

        # Build messages list: history + new user message
        messages: list[dict[str, Any]] = []
        for turn in history[-10:]:  # keep last 10 turns
            raw_role = turn.get("role", "user")
            # map assistant -> model for Gemini
            role = "model" if raw_role == "assistant" else "user"
            messages.append({
                "role": role,
                "parts": [{"text": turn["content"]}]
            })
        messages.append({
            "role": "user", 
            "parts": [{"text": message}]
        })

        if not config.GEMINI_API_KEY:
            raise ValueError("Missing GEMINI_API_KEY")

        headers = {
            "content-type": "application/json",
        }
        url = f"{config.GEMINI_ENDPOINT}?key={config.GEMINI_API_KEY}"
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": messages,
            "generationConfig": {"maxOutputTokens": 350},
        }
        resp = await _client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[llm_service] chat_with_context error: {exc}")
        return _CHAT_FALLBACK


# ---------------------------------------------------------------------------
# Per-zone staff action (admin dashboard)
# ---------------------------------------------------------------------------

STAFF_ACTION_SYSTEM = (
    "You are a venue operations AI. "
    "Given this single zone's current state, write ONE short staff action "
    "(under 12 words) for venue staff. "
    "Be specific and operational. "
    "Zone data: {zone_json}"
)

_STAFF_FALLBACK = "Monitor zone and report any queue buildup to supervisor."


async def get_staff_action(zone: dict[str, Any]) -> str:
    """Generate a single staff action recommendation for one zone.
    
    Args:
        zone: Zone data dict from crowd state
        
    Returns:
        Staff action string. Falls back to static response on error.
    """
    try:
        zone_json = json.dumps(
            {
                "name":         zone.get("name"),
                "type":         zone.get("type"),
                "density":      zone.get("density"),
                "wait_minutes": zone.get("wait_minutes"),
                "trend":        zone.get("trend"),
            }
        )
        system = STAFF_ACTION_SYSTEM.format(zone_json=zone_json)
        raw = await _call_gemini(system, "Provide the staff action now.", max_tokens=60)
        return raw.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[llm_service] get_staff_action error: {exc}")
        return _STAFF_FALLBACK
