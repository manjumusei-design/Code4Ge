"""Safe config loader, deep merge, coercion, and validation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from commitforge.types import Config
from commitforge.utils import _log, sanitize_path

logger = logging.getLogger("commitforge")

_DEFAULTS: Dict[str, Any] = {
    "ignore_paths": ["node_modules", ".git", ".venv", "__pycache__", "dist", "build"],
    "max_file_size_mb": 0.5,
    "severity_thresholds": {"warning": 3, "critical": 1},
    "commit_mappings": {
        "test": "test",
        "docs": "docs",
        "style": "style",
        "refactor": "refactor",
        "perf": "perf",
        "chore": "chore",
    },
}


def load_config(repo_root: Path) -> Config:
    """Read *repo_root/.commitforge.json*, deep-merge with defaults, return Config.

    Falls back to defaults on any I/O or parse error.
    """
    cfg_path = repo_root / ".commitforge.json"
    if not cfg_path.is_file():
        logger.debug("No config found; using defaults.")
        return validate_config(_DEFAULTS)
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            user = json.load(fh)
    except PermissionError as exc:
        _log(f"Permission denied: {cfg_path}: {exc}", logging.ERROR)
        return validate_config(_DEFAULTS)
    except json.JSONDecodeError as exc:
        _log(f"Malformed JSON in {cfg_path}: {exc}", logging.WARNING)
        return validate_config(_DEFAULTS)
    except ValueError as exc:
        _log(f"Invalid UTF-8 in {cfg_path}: {exc}", logging.WARNING)
        return validate_config(_DEFAULTS)
    except OSError as exc:
        _log(f"OS error reading {cfg_path}: {exc}", logging.ERROR)
        return validate_config(_DEFAULTS)
    merged = _deep_merge(dict(_DEFAULTS), user)
    return validate_config(merged)


def create_default_config(repo_root: Path) -> None:
    """Write default config only if file does not already exist."""
    target = repo_root / ".commitforge.json"
    if target.exists():
        _log(f"Config already exists: {target}", logging.WARNING)
        return
    try:
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(_DEFAULTS, fh, indent=2)
    except PermissionError as exc:
        _log(f"Cannot write config {target}: {exc}", logging.ERROR)


def validate_config(raw: Dict[str, Any]) -> Config:
    """Type-check *raw*, normalize paths, return a validated Config."""
    ignore = _coerce_list(raw.get("ignore_paths"), _DEFAULTS["ignore_paths"])
    ignore = [sanitize_path(str(p)) for p in ignore]
    size = _coerce_float(raw.get("max_file_size_mb"), 0.5, 0.01, 1024.0)
    thresholds = _coerce_dict(
        raw.get("severity_thresholds"), _DEFAULTS["severity_thresholds"]
    )
    mappings = _coerce_dict(
        raw.get("commit_mappings"), _DEFAULTS["commit_mappings"]
    )
    return Config(
        ignore_paths=ignore,
        max_file_size_mb=size,
        severity_thresholds=thresholds,
        commit_mappings=mappings,
    )


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into a copy of *base*. Side-effect-free."""
    result = dict(base)
    for key, val in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(val, dict)
        ):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _coerce_list(val: Any, default: list) -> list:
    """Return *val* if it is a list, otherwise *default*."""
    return val if isinstance(val, list) else default


def _coerce_float(val: Any, default: float, lo: float, hi: float) -> float:
    """Return *val* as float if numeric (not bool) and within bounds, else *default*."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return default
    fval = float(val)
    return fval if lo <= fval <= hi else default


def _coerce_dict(val: Any, default: dict) -> dict:
    """Return *val* if it is a dict, otherwise *default*."""
    return val if isinstance(val, dict) else default
