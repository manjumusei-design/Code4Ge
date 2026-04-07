"""Configuration loader and validator for commitforge"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from commitforge.types import Config
from commitforge.utils import log as _log

logger = logging.getLogger(__name__)
_CONFIG_FILE = ".commitforge.json"

_DEFAULTS = {
    "ignore_paths": ["node_modules", ".venv", "__pycache__", ".git", "dist"],
    "max_file_size_mb": 0.5,
    "severity_thresholds": {"warning": 3, "critical": 1},
    "commit_mappings": {
        "test": "test", "docs": "docs", "style": "style",
        "refactor": "refactor", "perf": "perf", "chore": "chore",
    },
}


def load_config(repo_root: Path) -> Config:
    """Read *repo_root/.commitforge.json*, merge with defaults, return Config."""
    cfg_path = repo_root / _CONFIG_FILE
    if not cfg_path.is_file():
        logger.debug("No config found; using defaults.")
        return validate_config(_DEFAULTS)
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            user = json.load(fh)
    except PermissionError as exc:
        _log("Permission denied: {} -- using defaults".format(cfg_path),
             logging.WARNING)
        return validate_config(_DEFAULTS)
    except (json.JSONDecodeError, OSError) as exc:
        _log("Bad config {}: {} -- using defaults".format(cfg_path, exc),
             logging.WARNING)
        return validate_config(_DEFAULTS)
    merged = _deep_merge(dict(_DEFAULTS), user)
    return validate_config(merged)


def create_default_config(repo_root: Path) -> None:
    """This writes a default config to repo root and deosnt overwrite the existing files"""
    target = repo_root / _CONFIG_FILE
    if target.exists():
        _log("Config already exists: {}".format(target), logging.WARNING)
        return
    try:
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(_DEFAULTS, fh, indent=2)
    except PermissionError as exc:
        _log("Cannot write config {}: {}".format(target, exc), logging.ERROR)


def validate_config(raw: Dict[str, Any]) -> Config:
    """Type-check *raw*, normalize paths, and to return a validated Config."""
    ignore = _coerce_list(raw.get("ignore_paths"), _DEFAULTS["ignore_paths"])
    size = _coerce_float(raw.get("max_file_size_mb"), 0.5, 0.01, 1024.0)
    thresholds = _coerce_dict(raw.get("severity_thresholds"),
                              _DEFAULTS["severity_thresholds"])
    mappings = _coerce_dict(raw.get("commit_mappings"),
                            _DEFAULTS["commit_mappings"])
    return Config(
        ignore_paths=[str(Path(p).as_posix()) for p in ignore],
        max_file_size_mb=size,
        severity_thresholds=thresholds,
        commit_mappings=mappings,
    )


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into a copy of *base*."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _coerce_list(val: Any, default: list) -> list:
    return val if isinstance(val, list) else default


def _coerce_float(val: Any, default: float, lo: float, hi: float) -> float:
    if isinstance(val, (int, float)) and lo <= val <= hi:
        return float(val)
    return default


def _coerce_dict(val: Any, default: dict) -> dict:
    return val if isinstance(val, dict) else default