"""Configuration loader and validator for commitforge"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

from commitforge import DEFAULT_CONFIG

logger = logging.getLogger (__name__)
ConfigType = Dict[str, Any]
CONFIG_FILENAME = ".commitforge.json"

def _deep_merge(base: ConfigType, override: ConfigType) -> None:
    """Recusively merge override into base in-place"""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
            
def _normalize(cfg: ConfigType) -> ConfigType:
    """Ensure legacy keys are migrated to current schema."""
    if "max_file_size_kb" in cfg:
        val = cfg.pop("max_file_size_kb")
        if isinstance(val, (int, float)):
            cfg["max_file_size_mb"] = val / 1024.0
        else:
            logger.warning(
                "Invalid max_file_size_kb value %r; using default", val
            )
            cfg["max_file_size_mb"] = DEFAULT_CONFIG.get("max_file_size_mb")
    return cfg


def load_config(repo_root: Path) -> ConfigType:
    """Load .commitforge.json from repo roots and to merge it with defaults"""
    cfg_path = repo_root / CONFIG_FILENAME
    if not cfg_path.is_file():
        logger.debug("No config found, using default configuration")
        return dict(DEFAULT_CONFIG)
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            user_cfg = json.load(fh)
    except PermissionError as exc:
        logger.warning("Permission denied reading %s: %s", cfg_path,exc)
        return dict(DEFAULT_CONFIG)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Bad config %s: %s -- using defaults.", cfg_path, exc)
        return dict(DEFAULT_CONFIG)
    merged=dict(DEFAULT_CONFIG)
    _deep_merge(merged, user_cfg)
    return _normalize(merged)

def load_config_from_cwd() -> ConfigType:
    """Try loading config from current working directory, or return to fallback which is the default value"""
    return load_config(Path.cwd())


def write_default_config(repo_root: Path) -> Path:
    """Write a default .commitforge.json to the repo and not to overwrite existing files"""
    target = repo_root / CONFIG_FILENAME
    if target.exists():
        logger.warning("Already exists: %s -- not overwriting.",target)
        return target
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_CONFIG, fh, indent=2)
    logger.info("Created default config at %s", target)
    return target

def validate_config(cfg: ConfigType) -> list[str]:
    """Return a list of schema validation warnings possible"""
    warnings: list[str] = []
    if not isinstance(cfg.get("ignored_paths"), list):
        warnings.append("'ignored_paths' should be a list.")
    max_sz = cfg.get("max_file_size_mb")
    if not isinstance(max_sz, (int, float)) or max_sz <= 0:
        warnings.append("'max_file_size_mb' must be a positive number.")
    for sev in ("warning", "critical"):
        val = cfg.get("severity_thresholds", {}).get(sev)
        if not isinstance(val, (int, float)) or val <= 0:
            warnings.append(f"'severity_thresholds.{sev}' must be positive.")
    return warnings