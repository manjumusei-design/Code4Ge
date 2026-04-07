"""Logging wrapper, path sanitization, and error formatters."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("commitforge")


def _log(message: str, level: int) -> None:
    """Log *message* at *level* with a timestamp if not already present."""
    if not any(
        message.startswith(prefix)
        for prefix in ("20", "[", "ERROR", "WARN", "INFO", "DEBUG")
    ):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        message = f"[{ts}] {message}"
    logger.log(level, "%s", message)


def sanitize_path(p: str) -> str:
    """Convert *p* to POSIX form, strip trailing slashes, normalize backslashes."""
    p = p.replace("\\", "/").rstrip("/")
    return p


def format_error(exc: Exception, context: str) -> str:
    """Return a consistent error-formatted string for logging."""
    return f"{context}: {exc.__class__.__name__}: {exc}"
