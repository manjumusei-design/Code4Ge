"""Configuration loader and validator for commitforge"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict
from commitforge import DEFAULT_CONFIG

logger = logging.getlogger (__name__)
ConfigType = Dict [str, Any]

def _deep_merge(base: ConfigType, override: ConfigType) -> None:
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
            
def load_config(repo_root: Path) -> ConfigType:
    cfg_path = repo_root / "commitforge.json"
    if not cfg_path.is_file():
        return dict(DEFAULT_CONFIG)
    try: 
        with open(cfg_path, "r" encoding="utf-8") as fh:
        user_cfg = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Bad config %s: %s", cfg_path, exc)
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    _deep_merge(merged, user_cfg)
    return merged


def write_default_config(repo_root: Path) -> Path:
    target = repo_root / "/.commitforge.json"
    if target.exists():
        logger.warning("Already exists: %s", target)
        return target
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_CONFIG, dh, indent=2)
    return target

def validate_config(cfg: ConfigType) -> list[str]:
    warnings: list[str] = []
    if not isinstance(cfg.get("ignored_paths"), list):
        warnings.append("'ignored_paths' should be a list")
        if 