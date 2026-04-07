"""commitforge -- Repository analysis and commit standardization tool."""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "Config",
    "Finding",
    "ScanResult",
    "CommitSuggestion",
    "load_config",
    "create_default_config",
    "validate_config",
    "scan_repo",
    "analyze_changes",
    "validate_commit_message",
    "app",
]

from commitforge.config import create_default_config, load_config, validate_config
from commitforge.analyzer import analyze_changes
from commitforge.scanner import scan_repo
from commitforge.validator import validate_commit_message
from commitforge.types import CommitSuggestion, Config, Finding, ScanResult
