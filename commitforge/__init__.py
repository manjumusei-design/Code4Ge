"""commitforge -- Repository analysis and commit standardization tool."""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "CheckIssue",
    "CommitSuggestion",
    "Config",
    "Finding",
    "ScanResult",
    "analyze_changes",
    "create_default_config",
    "get_checklist",
    "load_config",
    "run_checks",
    "scan_repo",
    "suggest_commit",
    "validate_commit_message",
    "validate_config",
    "app",
]

from commitforge.analyzer import analyze_changes, get_checklist, suggest_commit
from commitforge.checks import CheckIssue, run_checks
from commitforge.config import create_default_config, load_config, validate_config
from commitforge.scanner import scan_repo
from commitforge.validator import validate_commit_message
from commitforge.types import CommitSuggestion, Config, Finding, ScanResult
