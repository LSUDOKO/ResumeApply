from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()

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
            self.connections[session_id].remove(ws)
    
    async def broadcast(self, session_id: str, data: dict):
        if session_id in self.connections:
            for ws in self.connections[session_id]:
                try:
                    await ws.send_json(data)
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await manager.connect(session_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            # Handle voice responses or other UI feedback here
    except WebSocketDisconnect:
        manager.disconnect(session_id, ws)
