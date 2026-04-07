"""Code-health scanners for CommitForge."""

from __future__ import annotations

import ast
import collections
import logging
import re
from pathlib import Path
from typing import List

from commitforge.filters import apply_ignore
from commitforge.types import Config, Issue
from commitforge.utils import log

logger = logging.getLogger(__name__)
_BINARY_MARK = b"\x00"
_TODO_RE = re.compile(r"(?i)\b(TODO|FIXME|HACK|BUG)\b")
_IMPORT_RE = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+(.+)", re.MULTILINE)


def scan_large_files(repo_root: Path, config: Config) -> List[Issue]:
    """Return Issues for files exceeding config.max_file_size_mb."""
    issues: List[Issue] = []
    limit = config.max_file_size_mb * 1024 * 1024
    for fp in _iter_files(repo_root, config.ignore_paths):
        try:
            size = fp.stat().st_size
        except OSError:
            continue
        if size > limit:
            rel = str(fp.relative_to(repo_root))
            issues.append(Issue(rel, "large-file", "warning",
                                "{:.1f} MB exceeds {:.1f} MB limit".format(
                                    size / (1024 ** 2), config.max_file_size_mb)))
    return issues


def scan_binaries(repo_root: Path,
                  ignore_paths: List[str]) -> List[Issue]:
    """Detect binary files by checking for \\x00 in the first 512 bytes."""
    issues: List[Issue] = []
    for fp in _iter_files(repo_root, ignore_paths):
        try:
            chunk = fp.read_bytes()[:512]
        except OSError:
            continue
        if _BINARY_MARK in chunk:
            issues.append(Issue(str(fp.relative_to(repo_root)),
                                "binary-file", "warning",
                                "Binary content detected"))
    return issues


def scan_todos_fixmes(repo_root: Path,
                      ignore_paths: List[str]) -> List[Issue]:
    """Return one Issue per file containing 5+ TODO/FIXME/HACK/BUG markers."""
    issues: List[Issue] = []
    for fp in _iter_files(repo_root, ignore_paths):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        count = len(_TODO_RE.findall(text))
        if count >= 5:
            issues.append(Issue(str(fp.relative_to(repo_root)),
                                "excessive-todo", "warning",
                                "{} TODO/FIXME markers".format(count)))
    return issues


def scan_missing_docstrings(repo_root: Path,
                            ignore_paths: List[str]) -> List[Issue]:
    """Flag public functions/classes that lack a docstring."""
    issues: List[Issue] = []
    for fp in _iter_files(repo_root, ignore_paths):
        if fp.suffix != ".py":
            continue
        issues.extend(_check_docstrings(fp, repo_root))
    return issues


def scan_unused_imports(repo_root: Path,
                        ignore_paths: List[str]) -> List[Issue]:
    """Heuristic: find imported names that never appear elsewhere in the file."""
    issues: List[Issue] = []
    for fp in _iter_files(repo_root, ignore_paths):
        if fp.suffix != ".py":
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, lineno in _find_unused(text):
            issues.append(Issue(str(fp.relative_to(repo_root)),
                                "unused-import", "warning",
                                "'{}' imported but unused".format(name),
                                lineno))
    return issues


# Helpers

def _iter_files(root: Path, ignore: List[str]) -> List[Path]:
    """Yield files under *root*, skipping *ignore* patterns."""
    found: List[Path] = []
    for dirpath, dirs, names in root.walk():
        dirs[:] = [d for d in dirs if not apply_ignore(Path(d), ignore)]
        for name in names:
            fp = Path(dirpath) / name
            if not apply_ignore(fp, ignore):
                found.append(fp)
    return found


def _check_docstrings(filepath: Path, repo_root: Path) -> List[Issue]:
    """Return missing-docstring issues for a single Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8",
                                            errors="replace"),
                         filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        logger.debug("Cannot parse %s: %s", filepath, exc)
        return []
    rel = str(filepath.relative_to(repo_root))
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if not ast.get_docstring(node):
                issues.append(Issue(rel, "missing-docstring", "warning",
                                    "'{}' lacks a docstring".format(node.name),
                                    node.lineno))
    return issues


def _find_unused(text: str) -> List[tuple]:
    """Return ``[(name, lineno)]`` for likely unused imports."""
    imports: List[tuple] = []
    for match in _IMPORT_RE.finditer(text):
        for alias in match.group(1).split(","):
            name = alias.strip().split(" as ")[-1].split(".")[0].strip()
            if name and name != "*":
                imports.append((name, text[:match.start()].count("\n") + 1))
    if not imports:
        return []
    usage = collections.Counter(text.split())
    return [(n, ln) for n, ln in imports if usage.get(n, 0) <= 1]
