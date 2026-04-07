"""Commit-level result cache for CommitForge."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_CACHE_FILE = ".commitforge_cache.json"


def get_cache_key(repo_root: Path) -> Optional[str]:
    """Return SHA3-256 of repo_root + current HEAD commit hash."""
    try:
        import subprocess
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        logger.debug("Cannot resolve HEAD for cache key.")
        return None
    payload = "{}:{}".format(str(repo_root.resolve()), head)
    return hashlib.sha3_256(payload.encode("utf-8")).hexdigest()


def load_cache(repo_root: Path) -> Optional[Dict[str, Any]]:
    """Read .commitforge_cache.json and then return None on miss or stale data."""
    cache_path = repo_root / _CACHE_FILE
    if not cache_path.is_file():
        return None
    expected = get_cache_key(repo_root)
    if expected is None:
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    return data if data.get("cache_key") == expected else None


def save_cache(repo_root: Path, data: Dict[str, Any]) -> None:
    """Atomically write *data* to the cache file."""
    cache_path = repo_root / _CACHE_FILE
    key = get_cache_key(repo_root)
    if key is None:
        logger.debug("Skipping cache save: no HEAD.")
        return
    data["cache_key"] = key
    try:
        dir_ = cache_path.parent
        fd, tmp = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, str(cache_path))
    except OSError as exc:
        logger.warning("Cache write failed: %s", exc)
        try:
            os.unlink(tmp)
        except OSError:
            pass


def clear_cache(repo_root: Path) -> None:
    """Safely delete the cache file if it exists."""
    cache_path = repo_root / _CACHE_FILE
    try:
        if cache_path.is_file():
            cache_path.unlink()
            logger.debug("Cache cleared: %s", cache_path)
    except OSError as exc:
        logger.warning("Cannot clear cache %s: %s", cache_path, exc)
