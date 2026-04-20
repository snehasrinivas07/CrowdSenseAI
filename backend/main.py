"""
CrowdSense AI — FastAPI Backend
Endpoints: GET /crowd/state, POST /events/trigger, POST /nudges/generate,
           POST /chat, WebSocket /ws/crowd (pushes every 5 s)
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

import config
import simulator
from llm_service import chat_with_context, generate_nudges, get_staff_action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security & Logging Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses."""
    async def dispatch(self, request: Request, call_next) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP request method, path, and response time."""
    async def dispatch(self, request: Request, call_next) -> Any:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} {response.status_code} ({process_time:.3f}s)")
        return response


# Simple in-memory rate limiter for /chat
chat_limits: dict[str, float] = {}

def is_rate_limited(ip: str) -> bool:
    """Check if IP has exceeded rate limit (2 second cooldown between requests)."""
    now = time.time()
    last = chat_limits.get(ip, 0)
    if now - last < 2.0:
        return True
    chat_limits[ip] = now
    return False


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections for broadcast."""
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from active connections."""
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: str) -> None:
        """Broadcast data to all active WebSocket connections."""
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
app.add_middleware(RequestLoggingMiddleware)

# Restricted CORS for production safety
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class EventTriggerRequest(BaseModel):
    """Request body for POST /events/trigger."""
    event: str  # PRE_GAME | IN_PLAY | HALF_TIME | FULL_TIME


class ChatMessage(BaseModel):
    """Request body for POST /chat."""
    message: str
    history: list[dict[str, str]] = []


class StaffActionRequest(BaseModel):
    """Request body for POST /admin/staff-action."""
    zone_id: str


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health", summary="Health check")
async def health() -> dict[str, Any]:
    """Health check endpoint that returns service status, event, and zone count."""
    state = simulator.get_crowd_state()
    return {
        "status": "ok",
        "event": state["event"],
        "zone_count": 14
    }


@app.get("/crowd/state", summary="Get current crowd state for all 14 zones")
async def get_crowd_state() -> dict[str, Any]:
    """Retrieve current crowd state for all 14 stadium zones."""
    return simulator.get_crowd_state()


@app.post("/events/trigger", summary="Trigger a stadium event (PRE_GAME, HALF_TIME, etc.)")
async def trigger_event(req: EventTriggerRequest) -> dict[str, Any]:
    """Trigger a stadium event and update crowd simulation state."""
    event = req.event.strip().upper()
    try:
        simulator.set_event(event)
        return {"success": True, "status": "ok", "event": event}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/nudges/generate", summary="Generate LLM-powered attendee nudges")
async def nudges_generate() -> dict[str, Any]:
    """Generate LLM-powered nudges for current crowd state."""
    state = simulator.get_crowd_state()
    nudges = await generate_nudges(state)
    return {"event": state["event"], "nudges": nudges}


@app.post("/chat", summary="Crowd-aware natural language Q&A")
async def chat(req: ChatMessage, request: Request) -> dict[str, str]:
    """Answer crowd-related questions using LLM with current crowd state context."""
    # Input validation
    if not req.message or len(req.message.strip()) == 0:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    if len(req.message) > 500:
        raise HTTPException(status_code=422, detail="Message too long")
    
    # Rate limiting
    client_ip = request.client.host if request.client else "localhost"
    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before next request.")

    state = simulator.get_crowd_state()
    answer = await chat_with_context(req.message, req.history, state)
    return {"reply": answer}


@app.post("/admin/staff-action", summary="Get LLM staff action for a specific zone")
async def staff_action(req: StaffActionRequest) -> dict[str, str]:
    """Get LLM-generated staff action recommendation for a specific zone."""
    state = simulator.get_crowd_state()
    zone = next((z for z in state["zones"] if z["id"] == req.zone_id), None)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone '{req.zone_id}' not found.")
    action = await get_staff_action(zone)
    return {"zone_id": req.zone_id, "action": action}


@app.get("/admin/staff-actions", summary="Get LLM staff actions for ALL zones")
async def all_staff_actions() -> dict[str, Any]:
    """Get LLM-generated staff action recommendations for all zones."""
    state = simulator.get_crowd_state()
    actions = {}
    for zone in state["zones"]:
        actions[zone["id"]] = await get_staff_action(zone)
    return {"event": state["event"], "actions": actions}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/crowd")
async def websocket_crowd(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time crowd state updates (every 5 seconds)."""
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
