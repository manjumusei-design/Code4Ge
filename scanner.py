"""Anti-pattern detection and code-health scanning for CommitForge."""

from __future__ import annotations

import ast
import fnmatch
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

BINARY_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".exe", ".png", ".jpg", ".gif"}


@dataclass
class Issue:
    """A single health issue found in a file."""

    file: str
    rule: str
    severity: str
    message: str
    line: Optional[int] = None


def scan_large_files(
    root: Path, max_size_mb: float, ignored: Sequence[str] = ()
) -> List[Tuple[str, float]]:
    """Return list of (relative_path, size_mb) exceeding *max_size_mb*."""
    results: List[Tuple[str, float]] = []
    for fp in _iter_files(root, ignored):
        try:
            size_mb = fp.stat().st_size / (1024 * 1024)
        except OSError:
            continue
        if size_mb > max_size_mb:
            results.append((str(fp.relative_to(root)), round(size_mb, 2)))
    return results


def scan_binaries(root: Path, ignored: Sequence[str] = ()) -> List[str]:
    """Return list of relative paths detected as binary files."""
    results: List[str] = []
    for fp in _iter_files(root, ignored):
        if _is_binary(fp):
            results.append(str(fp.relative_to(root)))
    return results


def scan_todos(root: Path, ignored: Sequence[str] = ()) -> Dict[str, int]:
    """Return {file: count} of TODO/FIXME/HACK/BUG markers per file."""
    results: Dict[str, int] = {}
    pattern = re.compile(r"\b(TODO|FIXME|HACK|BUG)\b", re.IGNORECASE)
    for fp in _iter_files(root, ignored):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        count = len(pattern.findall(text))
        if count > 0:
            results[str(fp.relative_to(root))] = count
    return results

I wa
def scan_missing_docstrings(root: Path, ignored: Sequence[str] = ()) -> List[Issue]:
    """Return issues for public functions/classes without docstrings."""
    results: List[Issue] = []
    for fp in _iter_files(root, ignored):
        if fp.suffix != ".py":
            continue
        results.extend(_check_docstrings(fp, root))
    return results


def run_all_scans(
    root: Path,
    max_file_size_mb: float = 0.5,
    ignored_paths: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """Run every scanner and return a unified list of issue dicts."""
    issues: List[Dict[str, Any]] = []
    for path, size in scan_large_files(root, max_file_size_mb, ignored_paths):
        issues.append({"file": path, "rule": "large-file",
                        "severity": SEVERITY_WARNING,
                        "message": f"{size} MB (limit {max_file_size_mb} MB)",
                        "line": None})
    for path in scan_binaries(root, ignored_paths):
        issues.append({"file": path, "rule": "binary-file",
                        "severity": SEVERITY_INFO,
                        "message": "Binary file detected", "line": None})
    for path, count in scan_todos(root, ignored_paths).items():
        if count >= 5:
            issues.append({"file": path, "rule": "excessive-todo",
                            "severity": SEVERITY_WARNING,
                            "message": f"{count} TODO/FIXME markers", "line": None})
    for issue in scan_missing_docstrings(root, ignored_paths):
        issues.append({"file": issue.file, "rule": issue.rule,
                        "severity": issue.severity,
                        "message": issue.message, "line": issue.line})
    return issues


### Helper functions fore scanning assistance

def _is_binary(filepath: Path) -> bool:
    """Heuristic: known extensions or null byte in first 8 KB."""
    if filepath.suffix in BINARY_EXTENSIONS:
        return True
    try:
        return b"\x00" in filepath.read_bytes()[:8192]
    except OSError:
        return False


def _check_docstrings(filepath: Path, root: Path) -> List[Issue]:
    """Return missing-docstring issues for a single Python file."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except (OSError, SyntaxError):
        return []
    rel = str(filepath.relative_to(root))
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                issues.append(Issue(rel, "missing-docstring", SEVERITY_INFO,
                                    f"'{node.name}' lacks a docstring", node.lineno))
    return issues


def _iter_files(root: Path, ignored: Sequence[str]) -> List[Path]:
    """Yield files under *root*, skipping ignored patterns."""
    skip = set(ignored) | {".git"}
    files: List[Path] = []
    for dirpath, dirs, fnames in os.walk(root):
        dp = Path(dirpath)
        dirs[:] = [d for d in dirs if d not in skip and not _matches_any(d, ignored)]
        for fname in fnames:
            if not _matches_any(fname, ignored):
                files.append(dp / fname)
    return files


def _matches_any(name: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns