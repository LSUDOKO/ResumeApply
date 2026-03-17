from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json, asyncio, os
from lib.voice_helper import voice_helper

router = APIRouter()


@router.post("/session")
async def create_session(payload: dict):
    """Creates a new agent session and returns the session ID."""
    import uuid
    from lib.gcp_helper import gcp_helper
    session_id = str(uuid.uuid4())
    gcp_helper.save_session(session_id, {
        "profile": payload.get("profile", {}),
        "preferences": payload.get("preferences", {}),
        "applications": []
    })
    return {"session_id": session_id, "status": "created"}


@router.post("/session/{session_id}/answer")
async def session_answer(session_id: str, payload: dict):
    """Receives user input/answer for an active session (e.g. CAPTCHA resolution)."""
    from routers.websocket import _intervention_futures
    future = _intervention_futures.get(session_id)
    if future and not future.done():
        future.set_result(payload)
        return {"status": "delivered"}
    return {"status": "no_pending_intervention"}


@router.websocket("/ws/voice/{session_id}")
async def voice_session(websocket: WebSocket, session_id: str):
    """
    Real-time voice session handler.
    Receives binary audio (PCM16), transcribes via Google STT,
    and returns transcript events to the frontend.
    """
    await websocket.accept()
    print(f"Voice session started: {session_id}")

    # Thread-safe queue bridging async WebSocket → sync STT generator
    import queue
    sync_queue: queue.Queue = queue.Queue()

    def sync_audio_generator():
        """Sync generator consumed by the blocking Google STT client."""
        while True:
            chunk = sync_queue.get()
            if chunk is None:
                return
            yield chunk

    # Callback to send transcripts back on the async side
    transcript_queue: asyncio.Queue = asyncio.Queue()

    def run_stt():
        """Runs in a thread — calls blocking Google STT and pushes results."""
        try:
            responses = voice_helper.transcribe_stream(sync_audio_generator())
            for response in responses:
                if not response.results:
                    continue
                result = response.results[0]
                if not result.alternatives:
                    continue
                transcript_queue.put_nowait({
                    "type": "transcript",
                    "text": result.alternatives[0].transcript,
                    "is_final": result.is_final
                })
        except Exception as e:
            transcript_queue.put_nowait({"type": "stt_error", "error": str(e)})

    # Start STT in a background thread (non-blocking)
    stt_thread = asyncio.get_event_loop().run_in_executor(None, run_stt)

    async def send_transcripts():
        while True:
            msg = await transcript_queue.get()
            try:
                await websocket.send_json(msg)
            except Exception:
                break
            if msg.get("type") == "stt_error":
                break

    sender = asyncio.create_task(send_transcripts())

    try:
        while True:
            message = await websocket.receive()
            
            # Explicitly handle disconnect message type to avoid RuntimeError
            if message["type"] == "websocket.disconnect":
                print(f"Voice session disconnected: {session_id}")
                break

            if "bytes" in message:
                sync_queue.put(message["bytes"])
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "stop":
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        # Ignore normal disconnects that might still raise errors
        if not str(e).startswith("Cannot call"):
            print(f"WebSocket session error: {e}")
    finally:
        sync_queue.put(None)  # signal STT generator to stop
        sender.cancel()
        try:
            await stt_thread
        except Exception:
            pass
