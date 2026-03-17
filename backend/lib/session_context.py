import contextvars

# Global context variable to store the current session ID
current_session_id = contextvars.ContextVar("current_session_id", default=None)


async def check_pause():
    """
    Call at the start of every tool. If the session is paused, this suspends
    the coroutine until resume — zero CPU, pure asyncio Event wait.
    """
    session_id = current_session_id.get()
    if session_id:
        from routers.websocket import get_pause_event
        await get_pause_event(session_id).wait()
