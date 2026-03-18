from fastapi import APIRouter, BackgroundTasks
from agents.resume_agent import resume_agent
import asyncio
from lib.gcp_helper import gcp_helper

router = APIRouter()

# Track running agent tasks
_running_sessions: dict = {}

@router.post("/start")
async def start_agent(payload: dict, background_tasks: BackgroundTasks):
    session_id = payload["session_id"]
    preferences = payload["preferences"]
    voice_command = payload.get("voice_command", "")

    session_data = gcp_helper.get_session(session_id) or {}
    profile = session_data.get("profile", {})
    
    # Store preferences in session
    session_data["preferences"] = preferences
    gcp_helper.save_session(session_id, session_data)

    agent_context = (
        f"Voice Command: {voice_command}. "
        f"Job Preferences: {preferences}. "
        f"Candidate Profile: {profile}"
    )

    async def run_agent():
        from lib.session_context import current_session_id
        current_session_id.set(session_id)
        from routers.websocket import manager
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.genai import types as genai_types

        await manager.broadcast(session_id, {
            "type": "agent_started",
            "message": "Hyper-Speed Agent initializing..."
        })

        try:
            # Initialize a Runner for live event streaming
            session_service = InMemorySessionService()
            # MUST create the session in the ADK service first
            session_service.create_session(
                app_name="ResumeApply",
                user_id="default",
                session_id=session_id
            )
            
            runner = Runner(
                app_name="ResumeApply",
                agent=resume_agent,
                session_service=session_service
            )
            
            # Start a new message session
            user_msg = genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=agent_context)]
            )

            final_result = ""
            async for event in runner.run_async(
                user_id="default",
                session_id=session_id,
                new_message=user_msg
            ):
                print(f"DEBUG: Agent Event Received: {type(event)}")
                # Broadcast thoughts / reasoning
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"DEBUG: Agent Thinking: {part.text}")
                            await manager.broadcast(session_id, {
                                "type": "agent_thinking",
                                "text": part.text
                            })
                            if event.is_final_response():
                                final_result += part.text

                # Handle tool status updates for frontend feedback
                # Use actions.function_calls for ADK events
                if hasattr(event, "actions") and event.actions and event.actions.function_calls:
                    for call in event.actions.function_calls:
                        tool_name = getattr(call, "name", "tool")
                        print(f"DEBUG: Agent Tool Call: {tool_name}")
                        await manager.broadcast(session_id, {
                            "type": "agent_thinking",
                            "text": f"SYSTEM: Running tool: {tool_name}..."
                        })

            await manager.broadcast(session_id, {
                "type": "agent_complete",
                "summary": final_result or "Agent work finished."
            })
        except asyncio.CancelledError:
            await manager.broadcast(session_id, {
                "type": "agent_stopped",
                "message": "Agent stopped by user."
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            await manager.broadcast(session_id, {
                "type": "agent_error",
                "error": str(e)
            })
        finally:
            try:
                from tools.screenshot_tool import close_browser
                await close_browser(session_id)
            except Exception:
                pass
            from routers.websocket import cleanup_session
            cleanup_session(session_id)

    task = asyncio.create_task(run_agent())
    _running_sessions[session_id] = task
    return {"status": "started", "session_id": session_id}

@router.post("/stop")
async def stop_agent(payload: dict):
    session_id = payload["session_id"]
    if session_id in _running_sessions:
        _running_sessions[session_id].cancel()
        del _running_sessions[session_id]
    from routers.websocket import cleanup_session
    cleanup_session(session_id)
    return {"status": "stopped"}

@router.post("/pause")
async def pause_agent(payload: dict):
    session_id = payload["session_id"]
    from routers.websocket import manager, get_pause_event
    get_pause_event(session_id).clear()
    await manager.broadcast(session_id, {
        "type": "agent_paused",
        "message": payload.get("message", "Agent paused by user.")
    })
    return {"status": "paused"}

@router.post("/resume")
async def resume_agent_endpoint(payload: dict):
    session_id = payload["session_id"]
    from routers.websocket import manager, get_pause_event
    get_pause_event(session_id).set()
    await manager.broadcast(session_id, {
        "type": "agent_resumed",
        "message": "Agent resuming..."
    })
    return {"status": "resumed"}

@router.get("/results/{session_id}")
async def get_results(session_id: str):
    """Returns all applications logged for a session."""
    session_data = gcp_helper.get_session(session_id)
    if not session_data:
        return {"applications": [], "total_applied": 0, "total_skipped": 0, "session_id": session_id}

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
