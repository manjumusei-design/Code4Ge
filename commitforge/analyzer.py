"""Severity tracking, threshold evaluation, commit-type mapping."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from commitforge.checks import CheckIssue, run_checks
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


def _get_untracked_files(repo_root: Path) -> list[str]:
    """Get list of untracked file paths relative to repo root."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        _log(format_error(exc, "git ls-files --others"), logging.ERROR)
        return []

    return [
        line.strip()
        for line in result.stdout.strip().splitlines()
        if line.strip()
    ]


def _get_diff_stats(repo_root: Path) -> dict[str, dict[str, int]]:
    """Get diff stats per file: {path: {"added": N, "removed": N, "functions": [...]}}."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--numstat"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        _log(format_error(exc, "git diff --numstat"), logging.ERROR)
        return {}

    stats: dict[str, dict[str, int]] = {}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added, removed, path = parts
            stats[path] = {
                "added": int(added) if added != "-" else 0,
                "removed": int(removed) if removed != "-" else 0,
            }
    return stats


def _extract_functions_from_diff(repo_root: Path) -> dict[str, list[str]]:
    """Extract added/removed function names from git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "-U0", "--diff-filter=ACDMR"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return {}

    import re
    func_re = re.compile(r"^[+-]\s*(?:def|async def)\s+(\w+)\s*\(")
    current_file: str | None = None
    functions: dict[str, list[str]] = {}

    for line in result.stdout.splitlines():
        header = re.match(r"^diff --git a/.+ b/(.+)$", line)
        if header:
            current_file = header.group(1)
            functions[current_file] = []
            continue
        if current_file:
            match = func_re.match(line)
            if match:
                functions[current_file].append(match.group(1))

    return functions


def analyze_changes(
    repo_root: Path, config: Config, scan_result: ScanResult
) -> ScanResult:
    """Enrich scan_result with findings from tracked and untracked files."""
    severity_counts: dict[str, int] = {}

    # 1. Get diff stats for tracked files
    diff_stats = _get_diff_stats(repo_root)
    diff_functions = _extract_functions_from_diff(repo_root)

    for rel_path, stats in diff_stats.items():
        if _should_ignore(rel_path, config.ignore_paths):
            continue

        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue

        added = stats["added"]
        removed = stats["removed"]
        funcs = diff_functions.get(rel_path, [])

        # Build meaningful finding messages
        if funcs:
            for func in funcs:
                scan_result.findings.append(
                    Finding(
                        path=rel_path,
                        severity="info",
                        type="feat",
                        message=f"Added function `{func}()`",
                    )
                )
                severity_counts["info"] = severity_counts.get("info", 0) + 1
        elif added > 0 or removed > 0:
            severity = _classify_file(rel_path)
            finding_type = _map_commit_type(rel_path, config)
            status = _status_label("M")
            scan_result.findings.append(
                Finding(
                    path=rel_path,
                    severity=severity,
                    type=finding_type,
                    message=f"{status}: {added} added, {removed} removed",
                )
            )
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Run pre-commit checks
        issues = run_checks(abs_path, repo_root, is_new=False)
        for issue in issues:
            scan_result.findings.append(
                Finding(
                    path=rel_path,
                    severity=issue.severity,
                    type=issue.category,
                    message=issue.message,
                    line_number=issue.line_number,
                )
            )
            severity_counts[issue.severity] = (
                severity_counts.get(issue.severity, 0) + 1
            )

    # 2. Scan untracked files
    untracked = _get_untracked_files(repo_root)
    for rel_path in untracked:
        if _should_ignore(rel_path, config.ignore_paths):
            continue
        if rel_path in ("commitforge-report.html", "commitforge_report.html"):
            continue

        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue

        try:
            size = abs_path.stat().st_size
            if size > config.max_file_size_mb * 1024 * 1024:
                scan_result.findings.append(
                    Finding(
                        path=rel_path,
                        severity="critical",
                        type="chore",
                        message=f"Large file ({size / 1024 / 1024:.1f} MB) — consider git-lfs",
                    )
                )
                severity_counts["critical"] = severity_counts.get("critical", 0) + 1
                continue
        except OSError:
            continue

        if abs_path.suffix.lower() in _BINARY_EXTS:
            scan_result.findings.append(
                Finding(
                    path=rel_path,
                    severity="critical",
                    type="chore",
                    message="Binary file detected — verify it belongs in the repo",
                )
            )
            severity_counts["critical"] = severity_counts.get("critical", 0) + 1
            continue

        # Analyze new file content for functions
        try:
            content = abs_path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        found_funcs = False
        if abs_path.suffix.lower() == ".py":
            import re
            func_re = re.compile(r"^\s*(?:def|async def)\s+(\w+)\s*\(")
            for line in lines:
                match = func_re.match(line)
                if match:
                    scan_result.findings.append(
                        Finding(
                            path=rel_path,
                            severity="info",
                            type="feat",
                            message=f"New function `{match.group(1)}()`",
                        )
                    )
                    severity_counts["info"] = severity_counts.get("info", 0) + 1
                    found_funcs = True

        if not found_funcs:
            line_count = len(lines)
            scan_result.findings.append(
                Finding(
                    path=rel_path,
                    severity="info",
                    type="feat",
                    message=f"New file ({line_count} lines)",
                )
            )
            severity_counts["info"] = severity_counts.get("info", 0) + 1

        # Run pre-commit checks on new files
        issues = run_checks(abs_path, repo_root, is_new=True)
        for issue in issues:
            scan_result.findings.append(
                Finding(
                    path=rel_path,
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


def _should_ignore(rel_path: str, ignore_paths: list[str]) -> bool:
    """Check if a path matches any ignore pattern."""
    import fnmatch

    posix = rel_path.replace("\\", "/")
    name = Path(posix).name
    for pattern in ignore_paths:
        if fnmatch.fnmatch(posix, pattern):
            return True
        if fnmatch.fnmatch(name, pattern):
            return True
        if posix.startswith(pattern.rstrip("/*") + "/"):
            return True
    return False


def suggest_commit(
    config: Config,
    scan_result: ScanResult | None = None,
    scope: str | None = None,
    breaking: bool = False,
) -> CommitSuggestion:
    """Return a conventional CommitSuggestion from scan results."""
    if scan_result and scan_result.findings:
        types: dict[str, int] = {}
        for f in scan_result.findings:
            types[f.type] = types.get(f.type, 0) + 1

        commit_type = max(types, key=types.get) if types else "chore"

        # Count files changed
        files_changed = len({f.path for f in scan_result.findings})
        desc = f"update {files_changed} file{'s' if files_changed != 1 else ''}"

        # Check for TODOs to mention
        todos = [f for f in scan_result.findings if f.type == "todo"]
        if todos:
            desc = f"resolve TODO in {todos[0].path}"
            commit_type = "fix"
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
    """Extract actionable checklist items from scan results."""
    checklist: list[tuple[str, str, str]] = []
    for f in scan_result.findings:
        if f.type in ("debug", "secret", "test", "todo"):
            location = ""
            if f.line_number > 0:
                location = f"{f.path}:{f.line_number}"
            else:
                location = f.path
            checklist.append((f.severity.upper(), location, f.message))
    return checklist


def _classify_file(rel: str) -> str:
    """Assign severity based on file characteristics."""
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
