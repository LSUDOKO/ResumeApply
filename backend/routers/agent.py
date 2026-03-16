from fastapi import APIRouter, BackgroundTasks
from agents.resume_agent import resume_agent
import asyncio, os

router = APIRouter()

# Track running agent tasks
_running_sessions = {}

@router.post("/start")
async def start_agent(
    payload: dict,
    background_tasks: BackgroundTasks
):
    session_id = payload["session_id"]
    preferences = payload["preferences"]
    voice_command = payload.get("voice_command", "")
    
    from lib.supabase_db import db as supabase
    session_data = supabase.get_session(session_id)
    # session_data from supabase single() join returns a dict with 'profile' key
    profile = session_data.get("profile", {}) if session_data else {}

    agent_context = f"Voice Command: {voice_command}. Prefs: {preferences}. Profile: {profile}"
    
    async def run_agent():
        from lib.session_context import current_session_id
        current_session_id.set(session_id)
        from routers.websocket import manager
        await manager.broadcast(session_id, {"type": "agent_started", "message": "Opening LinkedIn..."})
        try:
            result = await resume_agent.run_async(user_message=agent_context, session_id=session_id)
            await manager.broadcast(session_id, {"type": "agent_complete", "summary": str(result)})
        except Exception as e:
            await manager.broadcast(session_id, {"type": "agent_error", "error": str(e)})

    _running_sessions[session_id] = asyncio.create_task(run_agent())
    return {"status": "started", "session_id": session_id}

@router.post("/stop")
async def stop_agent(payload: dict):
    session_id = payload["session_id"]
    if session_id in _running_sessions:
        _running_sessions[session_id].cancel()
        del _running_sessions[session_id]
    return {"status": "stopped"}
