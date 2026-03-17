from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json, asyncio, os
from lib.voice_helper import voice_helper

router = APIRouter()

@router.websocket("/ws/voice/{session_id}")
async def voice_session(websocket: WebSocket, session_id: str):
    """
    Real-time voice session handler.
    Receives binary audio (PCM16), transcribes via Google STT, 
    and returns text/audio responses.
    """
    await websocket.accept()
    print(f"Voice session started: {session_id}")

    # Queue to buffer audio chunks for the STT generator
    audio_queue = asyncio.Queue()

    async def audio_generator():
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                return
            yield chunk

    # Task to handle transcription responses from Google STT
    async def stt_task():
        try:
            responses = voice_helper.transcribe_stream(audio_generator())
            for response in responses:
                if not response.results:
                    continue
                
                result = response.results[0]
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript
                is_final = result.is_final

                # Send transcript back to frontend
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": is_final
                })

                if is_final:
                    print(f"Final Transcript: {transcript}")
                    # You could trigger agent logic here if needed
                    # For now, we'll confirm via TTS
                    # response_audio = voice_helper.synthesize_speech(f"Got it: {transcript}")
                    # await websocket.send_bytes(response_audio)

        except Exception as e:
            print(f"STT Error: {e}")

    # Start the STT processing in the background
    stt_proc = asyncio.create_task(stt_task())

    try:
        while True:
            # Receive binary audio or JSON metadata from frontend
            message = await websocket.receive()
            
            if "bytes" in message:
                await audio_queue.put(message["bytes"])
            elif "text" in message:
                data = json.loads(message["text"])
                if data.get("type") == "stop":
                    break
    except WebSocketDisconnect:
        print(f"Voice session disconnected: {session_id}")
    finally:
        await audio_queue.put(None)
        await stt_proc
