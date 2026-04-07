"""Severity tracking, threshold evaluation, commit-type mapping."""

from __future__ import annotations

import subprocess
from pathlib import Path

from commitforge.types import CommitSuggestion, Config, Finding, ScanResult
from commitforge.utils import _log, format_error

_DOC_EXTS = {".md", ".rst", ".txt", ".pyi"}
_TEST_EXTS = {".test.py", "_test.py", "test_"}
_STYLE_EXTS = {
    ".css", ".scss", ".sass", ".less", ".html",
    ".yaml", ".yml", ".toml", ".json",
}
_BINARY_EXTS = {".exe", ".dll", ".so", ".dylib", ".bin"}


def analyze_changes(
    repo_root: Path, config: Config, scan_result: ScanResult
) -> ScanResult:
    """Enrich *scan_result* with findings based on git status.

    Assigns severity per changed file, evaluates thresholds, and
    populates the findings list.
    """
    changed = _get_changed_files(repo_root)
    if not changed:
        scan_result.findings = []
        scan_result.thresholds_exceeded = False
        return scan_result

    severity_counts: dict[str, int] = {}
    for rel, status in changed:
        severity = _classify(rel, status)
        finding_type = _map_commit_type(rel, config)
        scan_result.findings.append(
            Finding(
                path=rel,
                severity=severity,
                type=finding_type,
                message=f"{status}: {rel}",
            )
        )
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    scan_result.thresholds_exceeded = _check_thresholds(
        severity_counts, config.severity_thresholds
    )
    return scan_result


def suggest_commit(
    config: Config, scope: str | None = None, breaking: bool = False
) -> CommitSuggestion:
    """Return a CommitSuggestion derived from configuration."""
    return CommitSuggestion(
        type="chore",
        scope=scope,
        description="update repository",
        breaking=breaking,
    )


def _get_changed_files(repo_root: Path) -> list[tuple[str, str]]:
    """Return [(rel_path, status_letter)] from git diff --name-status HEAD.

    Falls back to git status --porcelain for untracked files.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-status", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        _log(format_error(exc, "git diff"), logging.ERROR)
        return []

    if out.strip():
        entries: list[tuple[str, str]] = []
        for line in out.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                entries.append((parts[1], parts[0][0]))
        return entries

    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        _log(format_error(exc, "git status"), logging.ERROR)
        return []

    entries = []
    for line in out.strip().splitlines():
        if len(line) >= 3:
            status = line[0].strip()
            path = line[3:]
            if status:
                entries.append((path, status))
    return entries


def _classify(rel: str, status: str) -> str:
    """Assign severity based on file characteristics."""
    ext = Path(rel).suffix.lower()
    name = Path(rel).name.lower()
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
