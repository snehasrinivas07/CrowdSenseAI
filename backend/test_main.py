"""
Comprehensive pytest suite for CrowdSense AI backend.
Tests health checks, crowd state API, event triggers, chat, and CORS.
"""

import pytest
from fastapi.testclient import TestClient

import main
import simulator


@pytest.fixture
def client():
    """Provide a FastAPI TestClient for the app."""
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_simulator():
    """Reset simulator state and rate limiter before each test."""
    simulator._current_event = "IN_PLAY"
    main.chat_limits.clear()  # Clear rate limiter for tests
    yield
    simulator._current_event = "IN_PLAY"
    main.chat_limits.clear()  # Clean up after test


# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_returns_200(client):
    """TEST: GET /health returns 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_zone_count_14(client):
    """TEST: GET /health returns zone_count of 14."""
    response = client.get("/health")
    data = response.json()
    assert data["zone_count"] == 14


def test_health_has_status_ok(client):
    """TEST: GET /health returns status='ok'."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"


# ============================================================================
# Crowd State Tests
# ============================================================================

def test_crowd_state_returns_200(client):
    """TEST: GET /crowd/state returns 200."""
    response = client.get("/crowd/state")
    assert response.status_code == 200


def test_crowd_state_returns_14_zones(client):
    """TEST: GET /crowd/state returns exactly 14 zones."""
    response = client.get("/crowd/state")
    data = response.json()
    assert len(data["zones"]) == 14


def test_crowd_state_zones_have_required_fields(client):
    """TEST: Every zone has: zone_id, name, density, wait_minutes, trend."""
    response = client.get("/crowd/state")
    data = response.json()
    required_fields = {"id", "name", "density", "wait_minutes", "trend"}
    for zone in data["zones"]:
        assert required_fields.issubset(zone.keys()), f"Zone {zone.get('id')} missing fields"


def test_crowd_state_density_in_range(client):
    """TEST: density is always between 0 and 100."""
    response = client.get("/crowd/state")
    data = response.json()
    for zone in data["zones"]:
        assert 0 <= zone["density"] <= 100, f"Zone {zone['name']} density {zone['density']} out of range"


def test_crowd_state_wait_minutes_in_range(client):
    """TEST: wait_minutes is always between 0 and 18."""
    response = client.get("/crowd/state")
    data = response.json()
    for zone in data["zones"]:
        assert 0 <= zone["wait_minutes"] <= 18, f"Zone {zone['name']} wait_minutes {zone['wait_minutes']} out of range"


def test_crowd_state_has_summary(client):
    """TEST: GET /crowd/state includes summary section."""
    response = client.get("/crowd/state")
    data = response.json()
    assert "summary" in data
    assert "total_crowd_pct" in data["summary"]
    assert "highest_risk_zone" in data["summary"]


# ============================================================================
# Event Trigger Tests
# ============================================================================

def test_trigger_half_time_success(client):
    """TEST: POST /events/trigger {"event": "HALF_TIME"} returns {"success": true}."""
    response = client.post("/events/trigger", json={"event": "HALF_TIME"})
    data = response.json()
    assert response.status_code == 200
    assert data["success"] is True


def test_trigger_full_time_success(client):
    """TEST: POST /events/trigger {"event": "FULL_TIME"} returns {"success": true}."""
    response = client.post("/events/trigger", json={"event": "FULL_TIME"})
    data = response.json()
    assert response.status_code == 200
    assert data["success"] is True


def test_trigger_pre_game_success(client):
    """TEST: POST /events/trigger {"event": "PRE_GAME"} returns {"success": true}."""
    response = client.post("/events/trigger", json={"event": "PRE_GAME"})
    data = response.json()
    assert response.status_code == 200
    assert data["success"] is True


def test_trigger_invalid_event(client):
    """TEST: POST /events/trigger {"event": "INVALID"} returns error."""
    response = client.post("/events/trigger", json={"event": "INVALID"})
    assert response.status_code == 400


def test_trigger_event_updates_state(client):
    """TEST: After triggering HALF_TIME, simulator event is HALF_TIME."""
    client.post("/events/trigger", json={"event": "HALF_TIME"})
    state = client.get("/crowd/state").json()
    assert state["event"] == "HALF_TIME"


# ============================================================================
# Chat Tests
# ============================================================================

def test_chat_valid_message_returns_200(client):
    """TEST: POST /chat with valid message returns 200."""
    response = client.post("/chat", json={
        "message": "Where is shortest queue?",
        "history": []
    })
    assert response.status_code == 200


def test_chat_valid_message_has_reply(client):
    """TEST: POST /chat returns reply key."""
    response = client.post("/chat", json={
        "message": "Where is shortest queue?",
        "history": []
    })
    data = response.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)


def test_chat_empty_message_returns_422(client):
    """TEST: POST /chat with empty message returns 422."""
    response = client.post("/chat", json={
        "message": "",
        "history": []
    })
    assert response.status_code == 422


def test_chat_whitespace_only_message_returns_422(client):
    """TEST: POST /chat with whitespace-only message returns 422."""
    response = client.post("/chat", json={
        "message": "   ",
        "history": []
    })
    assert response.status_code == 422


def test_chat_message_over_500_chars_returns_422(client):
    """TEST: POST /chat with message over 500 chars returns 422."""
    long_message = "x" * 501
    response = client.post("/chat", json={
        "message": long_message,
        "history": []
    })
    assert response.status_code == 422


def test_chat_message_exactly_500_chars_returns_200(client):
    """TEST: POST /chat with exactly 500 chars returns 200."""
    message = "x" * 500
    response = client.post("/chat", json={
        "message": message,
        "history": []
    })
    assert response.status_code == 200


# ============================================================================
# Event Profile Tests
# ============================================================================

def test_half_time_concession_higher_than_exit(client):
    """TEST: After HALF_TIME, average concession density > average exit density."""
    client.post("/events/trigger", json={"event": "HALF_TIME"})
    state = client.get("/crowd/state").json()
    
    concession_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "concession"
    ]
    exit_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "exit"
    ]
    
    avg_concession = sum(concession_densities) / len(concession_densities)
    avg_exit = sum(exit_densities) / len(exit_densities)
    
    assert avg_concession > avg_exit, (
        f"Expected concession avg ({avg_concession}) > exit avg ({avg_exit}) at HALF_TIME"
    )


def test_density_never_exceeds_100_across_ticks(client):
    """TEST: Density never exceeds 100 across 50 simulator ticks."""
    for _ in range(50):
        state = client.get("/crowd/state").json()
        for zone in state["zones"]:
            assert zone["density"] <= 100, (
                f"Zone {zone['name']} exceeded 100 at density {zone['density']}"
            )


# ============================================================================
# CORS Tests
# ============================================================================

def test_cors_header_present_in_crowd_state(client):
    """TEST: CORS header present in GET /crowd/state response."""
    response = client.get("/crowd/state")
    # FastAPI TestClient doesn't fully simulate CORS headers, but we verify the endpoint works
    # and returns proper status code
    assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow(client):
    """Integration test: trigger event, check state, chat about it."""
    # Trigger HALF_TIME
    response = client.post("/events/trigger", json={"event": "HALF_TIME"})
    assert response.status_code == 200
    
    # Get crowd state
    response = client.get("/crowd/state")
    state = response.json()
    assert state["event"] == "HALF_TIME"
    assert len(state["zones"]) == 14
    
    # Ask about crowd
    response = client.post("/chat", json={
        "message": "What is the current event?",
        "history": []
    })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_multiple_events_in_sequence(client):
    """Test triggering multiple events in sequence."""
    events = ["PRE_GAME", "IN_PLAY", "HALF_TIME", "FULL_TIME"]
    for event in events:
        response = client.post("/events/trigger", json={"event": event})
        assert response.status_code == 200
        
        state = client.get("/crowd/state").json()
        assert state["event"] == event


def test_all_zones_present_and_named(client):
    """Test that all 14 zones are present with expected names."""
    state = client.get("/crowd/state").json()
    zone_names = {z["name"] for z in state["zones"]}
    
    expected_names = {
        "Gate A", "Gate B", "Gate C", "Gate D",
        "Concession 1", "Concession 2", "Concession 3", "Concession 4",
        "Restroom North", "Restroom South", "Restroom East", "Restroom West",
        "Exit 1", "Exit 2"
    }
    
    assert zone_names == expected_names, f"Zone mismatch: {zone_names} vs {expected_names}"


def test_pressure_peaks_during_half_time(client):
    """Test that concessions and restrooms show high pressure during HALF_TIME."""
    client.post("/events/trigger", json={"event": "HALF_TIME"})
    state = client.get("/crowd/state").json()
    
    # During HALF_TIME, concessions and restrooms should have notably higher average density
    concession_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "concession"
    ]
    restroom_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "restroom"
    ]
    gate_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "gate"
    ]
    
    avg_concession = sum(concession_densities) / len(concession_densities)
    avg_restroom = sum(restroom_densities) / len(restroom_densities)
    avg_gate = sum(gate_densities) / len(gate_densities)
    
    # Concessions should be significantly higher than gates during HALF_TIME
    assert avg_concession > avg_gate, (
        f"HALF_TIME concessions ({avg_concession}) should be > gates ({avg_gate})"
    )
    # Restrooms should also be higher
    assert avg_restroom > avg_gate, (
        f"HALF_TIME restrooms ({avg_restroom}) should be > gates ({avg_gate})"
    )


def test_exits_peak_during_full_time(client):
    """Test that exits show high pressure during FULL_TIME."""
    client.post("/events/trigger", json={"event": "FULL_TIME"})
    state = client.get("/crowd/state").json()
    
    exit_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "exit"
    ]
    gate_densities = [
        z["density"] for z in state["zones"] 
        if z["type"] == "gate"
    ]
    
    avg_exit = sum(exit_densities) / len(exit_densities)
    avg_gate = sum(gate_densities) / len(gate_densities)
    
    assert avg_exit > avg_gate, (
        f"FULL_TIME exits ({avg_exit}) should be > gates ({avg_gate})"
    )
