import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    """GET /health returns 200 and body contains {'status': 'ok'}"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "event" in data
    assert data["zone_count"] == 14

def test_crowd_state_structure():
    """GET /crowd/state returns 200 and response JSON contains a 'zones' key"""
    response = client.get("/crowd/state")
    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert isinstance(data["zones"], list)

def test_zone_count():
    """GET /crowd/state returns exactly 14 zones"""
    response = client.get("/crowd/state")
    data = response.json()
    assert len(data["zones"]) == 14

def test_zone_object_structure():
    """Every zone object contains: zone_id, name, density, wait_minutes, trend"""
    response = client.get("/crowd/state")
    data = response.json()
    for zone in data["zones"]:
        assert "id" in zone
        assert "name" in zone
        assert "density" in zone
        assert "wait_minutes" in zone
        assert "trend" in zone

def test_density_range():
    """density value for every zone is between 0 and 100 inclusive"""
    response = client.get("/crowd/state")
    data = response.json()
    for zone in data["zones"]:
        assert 0 <= zone["density"] <= 100

def test_wait_minutes_range():
    """wait_minutes value for every zone is between 0 and 18 inclusive"""
    response = client.get("/crowd/state")
    data = response.json()
    for zone in data["zones"]:
        assert 0 <= zone["wait_minutes"] <= 18

def test_trigger_half_time():
    """POST /events/trigger with body {'event': 'HALF_TIME'} returns {'success': true}"""
    response = client.post("/events/trigger", json={"event": "HALF_TIME"})
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_trigger_full_time():
    """POST /events/trigger with body {'event': 'FULL_TIME'} returns {'success': true}"""
    response = client.post("/events/trigger", json={"event": "FULL_TIME"})
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_trigger_invalid():
    """POST /events/trigger with body {'event': 'INVALID_EVENT'} returns {'success': false}"""
    response = client.post("/events/trigger", json={"event": "INVALID_EVENT"})
    # Status code might be 200 or 400 depending on implementation, 
    # but the requirement specifies the return body.
    assert response.json()["success"] is False

def test_chat_response():
    """POST /chat with body {'message': 'Where is the shortest queue?', 'history': []} returns 200 and response contains a 'reply' key"""
    response = client.post("/chat", json={"message": "Where is the shortest queue?", "history": []})
    assert response.status_code == 200
    assert "reply" in response.json()
