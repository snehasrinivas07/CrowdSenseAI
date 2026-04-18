"""
CrowdSense AI — Stadium Crowd Density Simulator
14 zones with sinusoidal density curves, event profiles, and noise modelling.
"""

import math
import random
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Zone definitions
# ---------------------------------------------------------------------------

ZONES: list[dict] = [
    {"id": "gate_a",  "name": "Gate A",         "type": "gate"},
    {"id": "gate_b",  "name": "Gate B",         "type": "gate"},
    {"id": "gate_c",  "name": "Gate C",         "type": "gate"},
    {"id": "gate_d",  "name": "Gate D",         "type": "gate"},
    {"id": "conc_1",  "name": "Concession 1",   "type": "concession"},
    {"id": "conc_2",  "name": "Concession 2",   "type": "concession"},
    {"id": "conc_3",  "name": "Concession 3",   "type": "concession"},
    {"id": "conc_4",  "name": "Concession 4",   "type": "concession"},
    {"id": "rest_n",  "name": "Restroom North",  "type": "restroom"},
    {"id": "rest_s",  "name": "Restroom South",  "type": "restroom"},
    {"id": "rest_e",  "name": "Restroom East",   "type": "restroom"},
    {"id": "rest_w",  "name": "Restroom West",   "type": "restroom"},
    {"id": "exit_1",  "name": "Exit 1",          "type": "exit"},
    {"id": "exit_2",  "name": "Exit 2",          "type": "exit"},
]

# ---------------------------------------------------------------------------
# Event profiles: maps event type → zone-type → density target (0.0–1.0)
# ---------------------------------------------------------------------------

EVENT_PROFILES: dict[str, dict[str, float]] = {
    "PRE_GAME": {
        "gate":       0.85,
        "concession": 0.55,
        "restroom":   0.30,
        "exit":       0.05,
    },
    "IN_PLAY": {
        "gate":       0.10,
        "concession": 0.25,
        "restroom":   0.20,
        "exit":       0.05,
    },
    "HALF_TIME": {
        "gate":       0.05,
        "concession": 0.90,
        "restroom":   0.85,
        "exit":       0.10,
    },
    "FULL_TIME": {
        "gate":       0.05,
        "concession": 0.20,
        "restroom":   0.40,
        "exit":       0.95,
    },
}

# Default idle profile when no event is active
_IDLE_PROFILE: dict[str, float] = {
    "gate":       0.15,
    "concession": 0.15,
    "restroom":   0.15,
    "exit":       0.05,
}

# ---------------------------------------------------------------------------
# Simulator state
# ---------------------------------------------------------------------------

_current_event: str = "IN_PLAY"          # active event key
_event_start_time: float = time.time()   # when the current event started


def set_event(event: str) -> None:
    """Switch the active event profile."""
    global _current_event, _event_start_time
    if event not in EVENT_PROFILES:
        raise ValueError(f"Unknown event: {event}. Valid: {list(EVENT_PROFILES)}")
    _current_event = event
    _event_start_time = time.time()


def get_current_event() -> str:
    return _current_event


# ---------------------------------------------------------------------------
# Density calculation helpers
# ---------------------------------------------------------------------------

def _zone_hash(zone_id: str) -> int:
    """Deterministic integer hash for a zone id (used for phase offset)."""
    return sum(ord(c) * (i + 1) for i, c in enumerate(zone_id))


def _compute_density(zone: dict, t: float) -> dict:
    """
    Compute the density state for a single zone at time t (seconds).

    density = target * 100 + sinusoidal_noise + random_noise
    noise    = sin(t * 0.3 + hash(zone_id) % 10) * 8 + random(-3, 3)
    wait_minutes = round(density / 100 * 18)   max 18 min
    trend: rising if noise > 3, falling if noise < -3, else stable
    predicted_spike_in_minutes: only concession/restroom during IN_PLAY
    """
    profile = EVENT_PROFILES.get(_current_event, _IDLE_PROFILE)
    target  = profile.get(zone["type"], 0.10)

    phase      = _zone_hash(zone["id"]) % 10
    sin_noise  = math.sin(t * 0.3 + phase) * 8
    rand_noise = random.uniform(-3, 3)
    noise      = sin_noise + rand_noise

    raw_density = target * 100 + noise
    density     = max(0.0, min(100.0, raw_density))

    wait_minutes = round(density / 100 * 18)

    if noise > 3:
        trend = "rising"
    elif noise < -3:
        trend = "falling"
    else:
        trend = "stable"

    result: dict = {
        "id":       zone["id"],
        "name":     zone["name"],
        "type":     zone["type"],
        "density":  round(density, 1),
        "wait_minutes": wait_minutes,
        "trend":    trend,
    }

    # Predicted spike only for concession/restroom during IN_PLAY
    if zone["type"] in ("concession", "restroom") and _current_event == "IN_PLAY":
        spike = max(0, round((100 - density) / 15))
        result["predicted_spike_in_minutes"] = spike

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_crowd_state() -> dict:
    """Return the full crowd state snapshot for all 14 zones."""
    t = time.time()
    zones_state = [_compute_density(zone, t) for zone in ZONES]

    total_crowd   = round(sum(z["density"] for z in zones_state) / len(zones_state))
    highest_risk  = max(zones_state, key=lambda z: z["density"])
    avg_wait      = round(sum(z["wait_minutes"] for z in zones_state) / len(zones_state))

    return {
        "timestamp":       t,
        "event":           _current_event,
        "zones":           zones_state,
        "summary": {
            "total_crowd_pct":    total_crowd,
            "highest_risk_zone":  highest_risk["name"],
            "highest_risk_density": highest_risk["density"],
            "avg_wait_minutes":   avg_wait,
        },
    }
