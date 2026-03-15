import contextvars

# Global context variable to store the current session ID
current_session_id = contextvars.ContextVar("current_session_id", default=None)
