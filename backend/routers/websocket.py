from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json, asyncio

router = APIRouter()

# Intervention futures: session_id -> asyncio.Future
_intervention_futures: Dict[str, asyncio.Future] = {}


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self.connections:
            self.connections[session_id] = []
        self.connections[session_id].append(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self.connections:
            try:
                self.connections[session_id].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, session_id: str, data: dict):
        if session_id not in self.connections:
            return
        dead = []
        for ws in self.connections[session_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)

    async def wait_for_intervention(self, session_id: str, timeout: float = 300.0) -> dict:
        """
        Blocks the agent until the user sends a response via WebSocket.
        Used for CAPTCHA, password prompts, etc.
        Returns the user's response payload.
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        _intervention_futures[session_id] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return {"type": "timeout"}
        finally:
            _intervention_futures.pop(session_id, None)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await manager.connect(session_id, ws)
    try:
        while True:
            raw = await ws.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type", "")

            # User resolved CAPTCHA or provided input
            if msg_type in ("intervention_response", "captcha_resolved", "user_input"):
                future = _intervention_futures.get(session_id)
                if future and not future.done():
                    future.set_result(message)

            # User sends a voice command mid-session
            elif msg_type == "voice_command":
                from routers.agent import _running_sessions
                # Broadcast back so frontend confirms receipt
                await manager.broadcast(session_id, {
                    "type": "voice_received",
                    "text": message.get("text", "")
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id, ws)
    except Exception as e:
        manager.disconnect(session_id, ws)
