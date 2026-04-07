"""Severity tracking, threshold evaluation, commit-type mapping."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from commitforge.checks import CheckIssue, run_checks
from commitforge.diff_parser import FileDiff, parse_diff
from commitforge.types import CommitSuggestion, Config, Finding, ScanResult
from commitforge.utils import _log, format_error

_DOC_EXTS = {".md", ".rst", ".txt", ".pyi"}
_TEST_EXTS = {".test.py", "_test.py", "test_"}
_STYLE_EXTS = {
    ".css", ".scss", ".sass", ".less", ".html",
    ".yaml", ".yml", ".toml", ".json",
}
_BINARY_EXTS = {".exe", ".dll", ".so", ".dylib", ".bin"}

_STATUS_LABELS = {
    "A": "Added",
    "M": "Modified",
    "D": "Deleted",
    "R": "Renamed",
    "C": "Copied",
    "U": "Updated",
    "?": "Untracked",
}


def _status_label(letter: str) -> str:
    """Return a human-readable status label."""
    return _STATUS_LABELS.get(letter, letter)


def analyze_changes(
    repo_root: Path, config: Config, scan_result: ScanResult
) -> ScanResult:
    """Enrich *scan_result* with findings based on git diff and pre-commit checks.

    Parses the actual diff to extract meaningful change descriptions,
    runs pre-commit checks on changed files, and evaluates thresholds.
    """
    file_diffs = parse_diff(repo_root)
    if not file_diffs:
        scan_result.findings = []
        scan_result.thresholds_exceeded = False
        return scan_result

    severity_counts: dict[str, int] = {}

    for fdiff in file_diffs:
        # Add findings from diff parsing
        for change in fdiff.changes:
            severity = _classify_change(change, fdiff)
            finding_type = _map_commit_type(fdiff.path, config)
            scan_result.findings.append(
                Finding(
                    path=fdiff.path,
                    severity=severity,
                    type=finding_type,
                    message=change.details,
                    line_number=change.line_number,
                )
            )
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # If no structured changes detected, add a generic finding
        if not fdiff.changes:
            total = fdiff.added_lines + fdiff.removed_lines
            if total > 0:
                severity = _classify_file(fdiff.path)
                finding_type = _map_commit_type(fdiff.path, config)
                status_text = _status_label(fdiff.status)
                scan_result.findings.append(
                    Finding(
                        path=fdiff.path,
                        severity=severity,
                        type=finding_type,
                        message=(
                            f"{status_text}: {fdiff.added_lines} added, "
                            f"{fdiff.removed_lines} removed"
                        ),
                    )
                )
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Run pre-commit checks on the actual file (only for changed files)
        abs_path = repo_root / fdiff.path
        if abs_path.is_file():
            issues = run_checks(abs_path, repo_root, is_new=fdiff.status == "A")
            for issue in issues:
                scan_result.findings.append(
                    Finding(
                        path=fdiff.path,
                        severity=issue.severity,
                        type=issue.category,
                        message=issue.message,
                        line_number=issue.line_number,
                    )
                )
                severity_counts[issue.severity] = (
                    severity_counts.get(issue.severity, 0) + 1
                )

    scan_result.thresholds_exceeded = _check_thresholds(
        severity_counts, config.severity_thresholds
    )
    return scan_result


def suggest_commit(
    config: Config,
    scan_result: ScanResult | None = None,
    scope: str | None = None,
    breaking: bool = False,
) -> CommitSuggestion:
    """Return a CommitSuggestion derived from scan results or defaults.

    If scan_result has findings, tries to build a specific description
    from the actual changes detected.
    """
    if scan_result and scan_result.findings:
        # Collect unique change types
        types: dict[str, int] = {}
        descriptions: list[str] = []
        for f in scan_result.findings:
            types[f.type] = types.get(f.type, 0) + 1
            if f.message and len(descriptions) < 3:
                descriptions.append(f.message)

        # Pick the most common type
        commit_type = max(types, key=types.get) if types else "chore"

        # Build description from first few findings
        if descriptions:
            desc = "; ".join(descriptions[:2])
            if len(desc) > 72:
                desc = desc[:69] + "..."
        else:
            desc = "update repository"
    else:
        commit_type = "chore"
        desc = "update repository"

    return CommitSuggestion(
        type=commit_type,
        scope=scope,
        description=desc,
        breaking=breaking,
    )


def get_checklist(scan_result: ScanResult) -> list[tuple[str, str, str]]:
    """Extract actionable checklist items from scan results.

    Returns:
        List of (severity, location, message) tuples for issues
        that should be addressed before committing.
    """
    checklist: list[tuple[str, str, str]] = []
    for f in scan_result.findings:
        # Only include actionable items (debug prints, secrets, missing tests, TODOs)
        if f.type in ("debug", "secret", "test", "todo"):
            location = ""
            if f.line_number > 0:
                location = f"{f.path}:{f.line_number}"
            else:
                location = f.path
            checklist.append((f.severity.upper(), location, f.message))
    return checklist


def _classify_change(change: "FileDiff", fdiff: "FileDiff") -> str:
    """Assign severity based on the type of change detected.

    Args:
        change: The specific change from diff parsing.
        fdiff: The file diff containing this change.

    Returns:
        Severity string: "critical", "warning", or "info".
    """
    # Removed functions/classes are potentially breaking
    if change.change_type == "removed" and change.kind in ("function", "class"):
        return "warning"

    # Added functions without tests will be caught by check_test_coverage
    if change.change_type == "added" and change.kind == "function":
        return "info"

    return "info"


def _classify_file(rel: str) -> str:
    """Assign severity based on file characteristics.

    Args:
        rel: Relative file path.

    Returns:
        Severity string: "critical", "warning", or "info".
    """
    ext = Path(rel).suffix.lower()
    if ext in _BINARY_EXTS:
        return "critical"
    parts = rel.lower().replace("\\", "/").split("/")
    is_test = any(
        p.startswith("test_") or p.endswith("_test.py")
        for p in parts
    )
    if is_test or ext in _TEST_EXTS:
        return "warning"
    if ext in _STYLE_EXTS or ext in _DOC_EXTS:
        return "info"
    return "info"


def _map_commit_type(rel: str, config: Config) -> str:
    """Return the commit type from config.commit_mappings, defaulting to 'chore'."""
    lower = rel.lower()
    for pattern, ctype in config.commit_mappings.items():
        if pattern.lower() in lower:
            return ctype
    return "chore"


def _check_thresholds(
    counts: dict[str, int], thresholds: dict[str, int]
) -> bool:
    """Return True if any severity count meets or exceeds its threshold."""
    for severity, threshold in thresholds.items():
        if counts.get(severity, 0) >= threshold:
            return True
    return False
