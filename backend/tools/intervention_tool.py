"""
human_intervention_tool.py
==========================
Production-grade human-in-the-loop gate.

What the original lacked:
  ✗ Didn't actually wait — just returned immediately and told the agent to "loop and check"
  ✗ No timeout — could block forever
  ✗ No screenshot context for the human
  ✗ No resolution signal path
  ✗ No retry / re-notify if human takes too long
  ✗ No per-session isolation of waiting state

What this version delivers:
  ✦ Real async wait    — agent truly suspends via asyncio.Event
  ✦ Session-isolated   — one Event per session, no cross-talk
  ✦ Screenshot on alert— human sees exactly what the agent sees
  ✦ Heartbeat pings    — re-broadcasts every 30 s so the UI never goes silent
  ✦ Configurable timeout — default 5 min, raises cleanly after
  ✦ resolve_intervention() — call from WebSocket handler to unblock the agent
  ✦ Typed reasons      — CAPTCHA / MFA / LOGIN / MANUAL_REVIEW / OTHER
  ✦ Full audit trail   — timestamps on request + resolution
"""

import asyncio
import base64
import io
import logging
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# In-process registry  {session_id: asyncio.Event}
# ─────────────────────────────────────────────────────
_pending: dict[str, asyncio.Event] = {}

InterventionReason = Literal["CAPTCHA", "MFA", "LOGIN", "MANUAL_REVIEW", "OTHER"]

DEFAULT_TIMEOUT_SEC   = 300   # 5 minutes
HEARTBEAT_INTERVAL    = 30    # re-ping every 30 s so the UI stays alive


# ─────────────────────────────────────────────────────
# Public: called by the WebSocket handler when the
# human clicks "I've resolved it" in the UI
# ─────────────────────────────────────────────────────
def resolve_intervention(session_id: str) -> bool:
    """
    Unblock a waiting agent for the given session.
    Returns True if there was a pending wait, False if nothing was waiting.

    Wire this into your WebSocket message handler:
        if data["type"] == "intervention_resolved":
            resolve_intervention(session_id)
    """
    event = _pending.get(session_id)
    if event and not event.is_set():
        event.set()
        logger.info("Intervention resolved for session %s", session_id)
        return True
    return False


# ─────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────
async def _get_screenshot_b64() -> str | None:
    """Grab current browser screenshot as a base64 PNG string."""
    try:
        from tools.screenshot_tool import get_browser
        _, page = await get_browser()
        raw = await page.screenshot(type="png")
        return base64.b64encode(raw).decode()
    except Exception as exc:
        logger.debug("Screenshot capture failed: %s", exc)
        return None


async def _broadcast(session_id: str, payload: dict) -> None:
    try:
        from routers.websocket import manager
        await manager.broadcast(session_id, payload)
    except Exception as exc:
        logger.warning("Broadcast failed for session %s: %s", session_id, exc)


async def _heartbeat_loop(
    session_id: str,
    reason: str,
    event: asyncio.Event,
    interval: int,
) -> None:
    """Re-broadcast the intervention alert every `interval` seconds until resolved."""
    count = 0
    while not event.is_set():
        await asyncio.sleep(interval)
        if event.is_set():
            break
        count += 1
        logger.debug("Heartbeat #%d for session %s", count, session_id)
        await _broadcast(session_id, {
            "type":    "human_intervention_required",
            "reason":  reason,
            "ping":    count,
            "message": f"⏳ Still waiting for human to resolve: {reason}  (ping #{count})",
        })


# ─────────────────────────────────────────────────────
# Main tool
# ─────────────────────────────────────────────────────
async def request_human_help_tool(
    reason: InterventionReason | str,
    context: str = "",
    screenshot_needed: bool = True,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> dict:
    """
    Pause the agent and wait for a human to resolve a blocker.

    Args:
        reason:           Why human help is needed (CAPTCHA / MFA / LOGIN /
                          MANUAL_REVIEW / OTHER).
        context:          Optional extra detail shown to the human
                          (e.g. "Google sign-in required on linkedin.com").
        screenshot_needed: Whether to attach a screenshot to the alert.
        timeout_sec:      Seconds to wait before giving up (default 300 = 5 min).

    Returns:
        {"status": "resolved", ...}   — human unblocked the agent
        {"status": "timeout",  ...}   — human didn't respond in time
        {"status": "error",    ...}   — session missing or other failure
    """
    from lib.session_context import current_session_id

    session_id = current_session_id.get()
    if not session_id:
        return {"status": "error", "reason": "No active session"}

    requested_at = datetime.now(timezone.utc).isoformat()

    # ── 1. Capture screenshot ────────────────────────────────────────────
    screenshot_b64 = await _get_screenshot_b64() if screenshot_needed else None

    # ── 2. Build and send the alert ──────────────────────────────────────
    alert_payload = {
        "type":          "human_intervention_required",
        "reason":        reason,
        "context":       context,
        "requested_at":  requested_at,
        "timeout_sec":   timeout_sec,
        "message":       _build_message(reason, context),
        "screenshot_b64": screenshot_b64,   # None if capture failed / not needed
    }
    await _broadcast(session_id, alert_payload)
    logger.info("Human intervention requested — session=%s reason=%s", session_id, reason)

    # ── 3. Create (or reuse) the per-session Event ────────────────────────
    event = asyncio.Event()
    _pending[session_id] = event

    # ── 4. Start heartbeat in background ────────────────────────────────
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(session_id, reason, event, HEARTBEAT_INTERVAL)
    )

    # ── 5. Actually wait ─────────────────────────────────────────────────
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_sec)
        resolved = True
    except asyncio.TimeoutError:
        resolved = False
    finally:
        heartbeat_task.cancel()
        _pending.pop(session_id, None)

    resolved_at = datetime.now(timezone.utc).isoformat()
    waited_sec  = _elapsed(requested_at, resolved_at)

    if resolved:
        await _broadcast(session_id, {
            "type":        "intervention_acknowledged",
            "reason":      reason,
            "resolved_at": resolved_at,
            "waited_sec":  waited_sec,
            "message":     "✅ Human resolved the blocker. Agent resuming.",
        })
        logger.info("Intervention resolved — session=%s waited=%.1fs", session_id, waited_sec)
        return {
            "status":      "resolved",
            "reason":      reason,
            "requested_at": requested_at,
            "resolved_at": resolved_at,
            "waited_sec":  waited_sec,
        }
    else:
        await _broadcast(session_id, {
            "type":    "intervention_timeout",
            "reason":  reason,
            "message": f"⚠️ Timed out after {timeout_sec}s waiting for human. Agent will skip this job.",
        })
        logger.warning("Intervention timed out — session=%s reason=%s", session_id, reason)
        return {
            "status":      "timeout",
            "reason":      reason,
            "requested_at": requested_at,
            "timeout_sec": timeout_sec,
            "waited_sec":  waited_sec,
        }


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def _build_message(reason: str, context: str) -> str:
    templates = {
        "CAPTCHA":       "🤖 CAPTCHA detected. Please solve it in the browser.",
        "MFA":           "🔐 Multi-factor authentication required. Please complete it.",
        "LOGIN":         "🔑 Manual login required. Please sign in.",
        "MANUAL_REVIEW": "👁 Manual review needed before the agent can continue.",
        "OTHER":         "⚠️ Agent is blocked and needs your help.",
    }
    base = templates.get(reason.upper(), templates["OTHER"])
    return f"{base}\n{context}".strip() if context else base


def _elapsed(iso_start: str, iso_end: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%S.%f+00:00"
    try:
        t0 = datetime.fromisoformat(iso_start)
        t1 = datetime.fromisoformat(iso_end)
        return round((t1 - t0).total_seconds(), 2)
    except Exception:
        return 0.0