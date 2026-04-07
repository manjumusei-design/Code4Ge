"""Shared utility helpers for CommitForge."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def detect_repo_root(cwd: Path) -> Optional[Path]:
    """Walk up from *cwd* until a .git directory is found.

    Returns the repository root Path, or None if not inside a Git repo.
    """
    current = cwd.resolve()
    candidates = [current] + list(current.parents)
    for parent in candidates:
        if (parent / ".git").exists():
            return parent
    return None


def safe_read_bytes(path: Path, limit_mb: int = 50) -> bytes:
    """Read up to *limit_mb* from *path* with encoding fallbacks.

    Attempts utf-8 first, then latin-1, then utf-8 with errors='ignore'.
    Returns empty bytes on OSError.
    """
    max_bytes = limit_mb * 1024 * 1024
    try:
        raw = path.read_bytes()[:max_bytes]
    except OSError as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return b""
    for encoding in ("utf-8", "latin-1"):
        try:
            raw.decode(encoding)
            return raw
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="ignore").encode("utf-8")


def get_terminal_size() -> Tuple[int, int]:
    """Return ``(columns, rows)`` of the current terminal.

    Falls back to ``(80, 24)`` when detection is unavailable.
    """
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return (size.columns, size.lines)
    except (AttributeError, OSError):
        return (80, 24)


def log(msg: str, level: int, quiet: bool = False) -> None:
    """Print *msg* at *level*, respecting the *quiet* flag.

    Non-error messages go to stdout; errors go to stderr.
    Logs to the module logger regardless of *quiet*.
    """
    if quiet and level < logging.ERROR:
        return
    dest = sys.stderr if level >= logging.ERROR else sys.stdout
    print(msg, file=dest)
    logger.log(level, msg)
