from fastapi import APIRouter, BackgroundTasks
from agents.resume_agent import resume_agent
import asyncio

router = APIRouter()

# Track running agent tasks
_running_sessions: dict = {}


@router.post("/start")
async def start_agent(payload: dict, background_tasks: BackgroundTasks):
    session_id = payload["session_id"]
    preferences = payload["preferences"]
    voice_command = payload.get("voice_command", "")

    from lib.local_db import db
    session_data = db.get_session(session_id)
    profile = session_data.get("profile", {}) if session_data else {}

    # Store preferences in session for tools to access
    session_data = session_data or {}
    session_data["preferences"] = preferences
    db.save_session(session_id, session_data)

    agent_context = (
        f"Voice Command: {voice_command}. "
        f"Job Preferences: {preferences}. "
        f"Candidate Profile: {profile}"
    )

    async def run_agent():
        from lib.session_context import current_session_id
        current_session_id.set(session_id)
        from routers.websocket import manager

        await manager.broadcast(session_id, {
            "type": "agent_started",
            "message": "Agent initializing browser..."
        })
        try:
            result = await resume_agent.run_async(
                user_message=agent_context,
                session_id=session_id
            )
            await manager.broadcast(session_id, {
                "type": "agent_complete",
                "summary": str(result)
            })
        except asyncio.CancelledError:
            await manager.broadcast(session_id, {
                "type": "agent_stopped",
                "message": "Agent stopped by user."
            })
        except Exception as e:
            await manager.broadcast(session_id, {
                "type": "agent_error",
                "error": str(e)
            })
        finally:
            # Clean up browser for this session
            try:
                from tools.screenshot_tool import close_browser
                await close_browser(session_id)
            except Exception:
                pass

    task = asyncio.create_task(run_agent())
    _running_sessions[session_id] = task
    return {"status": "started", "session_id": session_id}


@router.post("/stop")
async def stop_agent(payload: dict):
    session_id = payload["session_id"]
    if session_id in _running_sessions:
        _running_sessions[session_id].cancel()
        del _running_sessions[session_id]
    return {"status": "stopped"}


@router.post("/pause")
async def pause_agent(payload: dict):
    """Pause is handled via WebSocket message — this just broadcasts the pause event."""
    session_id = payload["session_id"]
    from routers.websocket import manager
    await manager.broadcast(session_id, {
        "type": "agent_paused",
        "message": payload.get("message", "Agent paused by user.")
    })
    return {"status": "paused"}


@router.post("/resume")
async def resume_agent_endpoint(payload: dict):
    session_id = payload["session_id"]
    from routers.websocket import manager
    await manager.broadcast(session_id, {
        "type": "agent_resumed",
        "message": "Agent resuming..."
    })
    return {"status": "resumed"}


@router.get("/results/{session_id}")
async def get_results(session_id: str):
    """Returns all applications logged for a session."""
    from lib.local_db import db
    session_data = db.get_session(session_id)
    if not session_data:
        return {"applications": [], "total_applied": 0, "total_skipped": 0}

    applications = session_data.get("applications", [])
    total_applied = sum(1 for a in applications if a.get("status") == "applied")
    total_skipped = sum(1 for a in applications if a.get("status") == "skipped")

    return {
        "applications": applications,
        "total_applied": total_applied,
        "total_skipped": total_skipped,
        "session_id": session_id
    }


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    is_running = session_id in _running_sessions and not _running_sessions[session_id].done()
    return {"session_id": session_id, "running": is_running}
