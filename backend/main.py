"""
CrowdSense AI — FastAPI Backend
Endpoints: GET /crowd/state, POST /events/trigger, POST /nudges/generate,
           POST /chat, WebSocket /ws/crowd (pushes every 5 s)
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import time

import simulator
from llm_service import chat_with_context, generate_nudges, get_staff_action

# ---------------------------------------------------------------------------
# Security & Rate Limiting
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        return response

# Simple in-memory rate limiter for /chat
chat_limits: dict[str, float] = {}

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    last = chat_limits.get(ip, 0)
    if now - last < 2.0: # 2 second cooldown
        return True
    chat_limits[ip] = now
    return False

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: str) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Background broadcast task
# ---------------------------------------------------------------------------

async def _broadcast_loop() -> None:
    """Push crowd state to all connected WebSocket clients every 5 seconds."""
    while True:
        state = simulator.get_crowd_state()
        payload = json.dumps(state)
        await manager.broadcast(payload)
        await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_broadcast_loop())
    yield
    task.cancel()


app = FastAPI(
    title="CrowdSense AI",
    description="Real-time crowd intelligence for large-scale sporting venues.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)

# Restricted CORS for production safety
PROD_FRONTEND = "https://crowdsense-frontend-417095097143.asia-south1.run.app"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[PROD_FRONTEND, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class EventTriggerRequest(BaseModel):
    event: str  # PRE_GAME | IN_PLAY | HALF_TIME | FULL_TIME


class ChatMessage(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class StaffActionRequest(BaseModel):
    zone_id: str


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/crowd/state", summary="Get current crowd state for all 14 zones")
async def get_crowd_state() -> dict[str, Any]:
    return simulator.get_crowd_state()


@app.post("/events/trigger", summary="Trigger a stadium event (PRE_GAME, HALF_TIME, etc.)")
async def trigger_event(req: EventTriggerRequest) -> dict[str, Any]:
    try:
        simulator.set_event(req.event)
        return {"success": True, "status": "ok", "event": req.event}
    except ValueError:
        return {"success": False, "status": "error"}


@app.post("/nudges/generate", summary="Generate LLM-powered attendee nudges")
async def nudges_generate() -> dict[str, Any]:
    state  = simulator.get_crowd_state()
    nudges = await generate_nudges(state)
    return {"event": state["event"], "nudges": nudges}


@app.post("/chat", summary="Crowd-aware natural language Q&A")
async def chat(req: ChatMessage, request: Request) -> dict[str, str]:
    # Rate limiting
    client_ip = request.client.host
    if is_rate_limited(client_ip):
        return {"reply": "I'm thinking a bit too fast! Please wait a second before your next question."}

    state  = simulator.get_crowd_state()
    answer = await chat_with_context(req.message, req.history, state)
    return {"reply": answer}


@app.post("/admin/staff-action", summary="Get LLM staff action for a specific zone")
async def staff_action(req: StaffActionRequest) -> dict[str, str]:
    state = simulator.get_crowd_state()
    zone  = next((z for z in state["zones"] if z["id"] == req.zone_id), None)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone '{req.zone_id}' not found.")
    action = await get_staff_action(zone)
    return {"zone_id": req.zone_id, "action": action}


@app.get("/admin/staff-actions", summary="Get LLM staff actions for ALL zones")
async def all_staff_actions() -> dict[str, Any]:
    state   = simulator.get_crowd_state()
    actions = {}
    for zone in state["zones"]:
        actions[zone["id"]] = await get_staff_action(zone)
    return {"event": state["event"], "actions": actions}


@app.get("/health", summary="Health check")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "backend": "Vercel" if os.environ.get("VERCEL") else "CloudRun",
        "zone_count": 14
    }

@app.get("/debug/gemini")
async def debug_gemini():
    """Diagnostic endpoint to find the working model for this environment."""
    from llm_service import get_gemini_config
    import httpx
    
    url_base, key = get_gemini_config()
    key_masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "NOT_SET"
    
    models_to_test = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro", "gemini-1.5-pro"]
    results = {}
    
    for model in models_to_test:
        test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(test_url, json={
                    "contents": [{"parts": [{"text": "hi"}]}]
                })
                if resp.status_code == 200:
                    results[model] = "✅ WORKING"
                else:
                    results[model] = f"❌ ERROR ({resp.status_code}): {resp.json().get('error', {}).get('message', 'Unknown')}"
        except Exception as e:
            results[model] = f"❌ EXCEPTION: {str(e)}"
            
    return {
        "key_present": bool(key),
        "key_preview": key_masked,
        "model_tests": results,
    }


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/crowd")
async def websocket_crowd(ws: WebSocket) -> None:
    await manager.connect(ws)
    # Send immediate snapshot on connect so the client doesn't wait 5 s
    state = simulator.get_crowd_state()
    await ws.send_text(json.dumps(state))
    try:
        while True:
            # Keep connection alive; actual broadcast happens in _broadcast_loop
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
