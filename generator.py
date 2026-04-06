"""Conventional commit message generation for CommitForge."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from commitforge.parser import DiffResult, FileChange

# Heuristics
_COMMIT_TYPE_KEYWORDS: Dict[str, Sequence[str]] = {
    "feat": ["add", "create", "introduce", "implement", "new"],
    "fix": ["fix", "resolve", "patch", "correct", "bug"],
    "docs": ["doc", "readme", "comment", "typo", "guide"],
    "style": ["format", "whitespace", "lint", "indent", "style"],
    "refactor": ["refactor", "restructure", "reorganize", "clean", "simplify"],
    "perf": ["optimize", "speed", "performance", "cache", "lazy", "memoize"],
    "test": ["test", "spec", "coverage", "assert", "unittest"],
    "chore": ["update", "bump", "ignore", "config", "ci", "build", "deps"],
}

_SCOPE_HINTS: Dict[str, str] = {
    "readme.md": "docs", "docs/": "docs", "tests/": "test",
    "test/": "test", "ci/": "ci", ".github/": "ci",
    "setup.py": "build", "pyproject.toml": "build",
    "requirements.txt": "deps",
}


def generate_commit_suggestion(diff: DiffResult) -> Dict[str, str]:
    """Return a conventional commit message based on the diff.
    
    Returns ``{"type": str, "scope": str, "summary": str, "body": str}``.
    """
    if not diff.files:
        return {"type": "chore", "scope": "", "summary": "no changes detected", "body": ""}

    ctype = _infer_type(diff.files)
    scope = _infer_scope(diff.files)
    summary = _build_summary_line(diff.files)
    body = _build_body(diff.files)
    return {"type": ctype, "scope": scope, "summary": summary, "body": body}


def _infer_type(files: List[FileChange]) -> str:
    """Pick the most likely conventional commit type from changed files."""
    scores: Counter[str] = Counter()
    for fc in files:
        text = (fc.path + " " + " ".join(fc.hunks)).lower()
        for ctype, keywords in _COMMIT_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[ctype] += 1
    if all(f.status == "D" for f in files):
        scores["chore"] += 2
    if not scores:
        return _type_by_extension(files)
    return scores.most_common(1)[0][0]


def _type_by_extension(files: List[FileChange]) -> str:
    """Fallback: guess type from file extensions."""
    if any(f.path.endswith((".md", ".rst", ".txt")) for f in files):
        return "docs"
    if any(f.path.endswith((".cfg", ".toml", ".ini", ".json", ".yaml", ".yml"))
           for f in files):
        return "chore"
    return "feat"


def _infer_scope(files: List[FileChange]) -> Optional[str]:
    """Extract an optional scope from common directory hints."""
    for fc in files:
        for hint, scope in _SCOPE_HINTS.items():
            if fc.path.startswith(hint) or fc.path.endswith(hint):
                return scope
    return ""


def _build_summary_line(files: List[FileChange]) -> str:
    """Create a one-line summary under 72 characters."""
    if len(files) == 1:
        return _shorten(files[0].path, 60)
    return f"Update {len(files)} files"


def _build_body(files: List[FileChange]) -> str:
    """List changed files (max 10) with status labels."""
    lines: List[str] = []
    for fc in files[:10]:
        status_label = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(
            fc.status, "changed"
        )
        lines.append(f"- {status_label} `{fc.path}`")
    if len(files) > 10:
        lines.append(f"... and {len(files) - 10} more")
    return "\n".join(lines)


def _shorten(text: str, max_len: int) -> str:
    """Truncate *text* with ellipsis if it exceeds *max_len*."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_commit(commit: Dict[str, str]) -> str:
    """Render a commit dict into a conventional commit string."""
    prefix = f"{commit['type']}({commit['scope']})" if commit["scope"] else commit["type"]
    header = f"{prefix}: {commit['summary']}"
    if commit["body"]:
        return f"{header}\n\n{commit['body']}"
    return header


def _extract_keywords_from_hunks(hunks: List[str]) -> List[str]:
    """Return unique keywords found in diff hunk lines (unused helper)."""
    found: List[str] = []
    keyword_pattern = re.compile(r"\b(TODO|FIXME|BUG|HACK|XXX)\b", re.IGNORECASE)
    for hunk in hunks:
        for line in hunk.splitlines():
            if line.startswith("+"):
                found.extend(keyword_pattern.findall(line))
    return list(dict.fromkeys(found))
