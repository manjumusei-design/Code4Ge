"""Pre-commit checks: debug prints, TODOs, secrets, missing tests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate potential issues that are usually indicative of bad behaviour imo
_DEBUG_PRINT_RE = re.compile(
    r"""(?x)
    ^\s*(?:
        print\s*\(
        |pprint\s*\(
        |console\.log\s*\(
        |debugger\s*;
    )
    """,
)
_TODO_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG|TEMP)\b", re.IGNORECASE)
_SECRET_RE = re.compile(
    r"""(?:password|secret|api_key|apikey|token|auth_key|private_key)\s*=\s*["'][^"']{4,}["']""",
    re.IGNORECASE,
)
_HARDCODED_IP_RE = re.compile(
    r"""(?:https?://|ftp://)(?:\d{1,3}\.){3}\d{1,3}""",
)
_LONG_LINE_RE = re.compile(r".{120,}")
_DEPRECATED_RE = re.compile(
    r"\b(deprecated|obsolete|legacy|workaround|temporary)\b",
    re.IGNORECASE,
)


@dataclass
class CheckIssue:
    """A single issue found by a pre-commit check."""

    severity: str  # "critical", "warning", "info"
    category: str  # "debug", "todo", "secret", "style", "test"
    message: str
    line_number: int = 0
    line_content: str = ""


def run_checks(file_path: Path, repo_root: Path, is_new: bool = False) -> List[CheckIssue]:
    """Run all pre-commit checks on a single file.

    Args:
        file_path: Absolute path to the file.
        repo_root: Absolute path to the repository root.
        is_new: If True, the file is newly added (stricter checks).

    Returns:
        List of CheckIssue objects found in the file.
    """
    issues: List[CheckIssue] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    lines = content.splitlines()

    issues.extend(_check_debug_prints(lines, file_path))
    issues.extend(_check_todos(lines, file_path))
    issues.extend(_check_secrets(lines, file_path))
    issues.extend(_check_long_lines(lines, file_path))
    issues.extend(_check_deprecated_comments(lines, file_path))

    # Test coverage check only for new source files
    if is_new and _is_source_file(file_path):
        issues.extend(_check_test_coverage(file_path, repo_root))

    return issues


def _check_debug_prints(lines: List[str], file_path: Path) -> List[CheckIssue]:
    """Check for debug print statements.

    Args:
        lines: File content split into lines.
        file_path: Path to the file.

    Returns:
        List of CheckIssue for each debug print found.
    """
    issues: List[CheckIssue] = []
    for i, line in enumerate(lines, 1):
        if _DEBUG_PRINT_RE.search(line):
            # Skip if it's in a comment or string literal that looks intentional
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            issues.append(
                CheckIssue(
                    severity="critical",
                    category="debug",
                    message=f"Debug print detected: `{stripped.strip()[:60]}`",
                    line_number=i,
                    line_content=stripped,
                )
            )
    return issues


def _check_todos(lines: List[str], file_path: Path) -> List[CheckIssue]:
    """Check for TODO/FIXME/HACK comments.

    Args:
        lines: File content split into lines.
        file_path: Path to the file.

    Returns:
        List of CheckIssue for each TODO-style comment.
    """
    issues: List[CheckIssue] = []
    for i, line in enumerate(lines, 1):
        match = _TODO_RE.search(line)
        if match:
            issues.append(
                CheckIssue(
                    severity="warning",
                    category="todo",
                    message=f"{match.group(1).upper()}: `{line.strip()[:60]}`",
                    line_number=i,
                    line_content=line.strip(),
                )
            )
    return issues


def _check_secrets(lines: List[str], file_path: Path) -> List[CheckIssue]:
    """Check for hardcoded secrets and credentials.

    Args:
        lines: File content split into lines.
        file_path: Path to the file.

    Returns:
        List of CheckIssue for each potential secret found.
    """
    issues: List[CheckIssue] = []
    for i, line in enumerate(lines, 1):
        if _SECRET_RE.search(line):
            issues.append(
                CheckIssue(
                    severity="critical",
                    category="secret",
                    message="Hardcoded secret detected — use environment variables",
                    line_number=i,
                    line_content=line.strip()[:60],
                )
            )
        if _HARDCODED_IP_RE.search(line):
            issues.append(
                CheckIssue(
                    severity="warning",
                    category="secret",
                    message="Hardcoded IP address — consider using configuration",
                    line_number=i,
                    line_content=line.strip()[:60],
                )
            )
    return issues


def _check_long_lines(lines: List[str], file_path: Path) -> List[CheckIssue]:
    """Check for lines exceeding 120 characters.

    Args:
        lines: File content split into lines.
        file_path: Path to the file.

    Returns:
        List of CheckIssue for each long line.
    """
    issues: List[CheckIssue] = []
    for i, line in enumerate(lines, 1):
        if _LONG_LINE_RE.match(line):
            issues.append(
                CheckIssue(
                    severity="info",
                    category="style",
                    message=f"Line too long ({len(line)} chars, max 120)",
                    line_number=i,
                    line_content="",
                )
            )
    return issues


def _check_deprecated_comments(lines: List[str], file_path: Path) -> List[CheckIssue]:
    """Check for deprecated/legacy/workaround comments.

    Args:
        lines: File content split into lines.
        file_path: Path to the file.

    Returns:
        List of CheckIssue for each deprecated comment.
    """
    issues: List[CheckIssue] = []
    for i, line in enumerate(lines, 1):
        if _DEPRECATED_RE.search(line):
            issues.append(
                CheckIssue(
                    severity="warning",
                    category="style",
                    message=f"Deprecated code marker: `{line.strip()[:60]}`",
                    line_number=i,
                    line_content=line.strip(),
                )
            )
    return issues


def _check_test_coverage(
    file_path: Path, repo_root: Path
) -> List[CheckIssue]:
    """Check if a source file has a corresponding test file.

    Args:
        file_path: Absolute path to the source file.
        repo_root: Absolute path to the repository root.

    Returns:
        List with one CheckIssue if no test file found.
    """
    rel = file_path.relative_to(repo_root)
    rel_str = str(rel).replace("\\", "/")

    # Skip if already a test file
    if _is_test_file(rel_str):
        return []

    # Look for test files
    test_patterns = [
        repo_root / "tests" / f"test_{file_path.name}",
        repo_root / "tests" / f"{file_path.stem}_test.py",
        repo_root / "test" / f"test_{file_path.name}",
        file_path.parent / f"test_{file_path.name}",
        file_path.parent / f"{file_path.stem}_test.py",
    ]

    for pattern in test_patterns:
        if pattern.exists():
            return []

    # Also check for any test file containing the module name
    test_dirs = [repo_root / "tests", repo_root / "test"]
    for test_dir in test_dirs:
        if test_dir.is_dir():
            for test_file in test_dir.rglob("test_*.py"):
                if file_path.stem in test_file.stem:
                    return []

    return [
        CheckIssue(
            severity="warning",
            category="test",
            message=f"No test file found for `{rel}` — consider adding tests",
            line_number=0,
            line_content="",
        )
    ]


def _is_source_file(file_path: Path) -> bool:
    """Check if a file is a source code file.

    Args:
        file_path: Path to check.

    Returns:
        True if the file is a source code file.
    """
    source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp"}
    return file_path.suffix.lower() in source_exts


def _is_test_file(rel_path: str) -> bool:
    """Check if a relative path looks like a test file.

    Args:
        rel_path: Relative path string (POSIX style).

    Returns:
        True if the path appears to be a test file.
    """
    lower = rel_path.lower()
    return (
        "test_" in lower
        or "_test." in lower
        or lower.startswith("tests/")
        or lower.startswith("test/")
    )


def summarize_issues(issues: List[CheckIssue]) -> List[Tuple[str, str, str]]:
    """Format check issues into a summary list.

    Args:
        issues: List of CheckIssue objects.

    Returns:
        List of (severity, location, message) tuples.
    """
    result: List[Tuple[str, str, str]] = []
    for issue in issues:
        location = ""
        if issue.line_number > 0:
            location = f"line {issue.line_number}"
        result.append((issue.severity.upper(), location, issue.message))
    return result
