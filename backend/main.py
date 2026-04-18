"""
CrowdSense AI — FastAPI Backend
Endpoints: GET /crowd/state, POST /events/trigger, POST /nudges/generate,
           POST /chat, WebSocket /ws/crowd (pushes every 5 s)
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import simulator
from llm_service import chat_with_context, generate_nudges, get_staff_action

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
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
async def trigger_event(req: EventTriggerRequest) -> dict[str, str]:
    try:
        simulator.set_event(req.event)
        return {"status": "ok", "event": req.event}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/nudges/generate", summary="Generate LLM-powered attendee nudges")
async def nudges_generate() -> dict[str, Any]:
    state  = simulator.get_crowd_state()
    nudges = await generate_nudges(state)
    return {"event": state["event"], "nudges": nudges}


@app.post("/chat", summary="Crowd-aware natural language Q&A")
async def chat(req: ChatMessage) -> dict[str, str]:
    state  = simulator.get_crowd_state()
    answer = await chat_with_context(req.message, req.history, state)
    return {"answer": answer}


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
async def health() -> dict[str, str]:
    return {"status": "healthy", "event": simulator.get_current_event()}


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
