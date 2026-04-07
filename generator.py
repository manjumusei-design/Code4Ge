"""Conventional commit message generation for CommitForge."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from commitforge.types import Config, DiffResult, FileChange

# Heuristics
_COMMIT_KEYWORDS: Dict[str, List[str]] = {
    "fix": ["fix", "bug", "patch", "crash", "error", "fail"],
    "docs": ["doc", "readme", "typo", "guide", "manual", "comment"],
    "style": ["format", "whitespace", "lint", "indent", "prettier"],
    "refactor": ["refactor", "restructure", "reorganize", "simplify"],
    "perf": ["optimize", "speed", "performance", "cache", "lazy"],
    "test": ["test", "spec", "coverage", "assert", "unittest"],
    "chore": ["ignore", "ci", "build", "deps", "vendor", "bump"],
}

def suggest_commit(result: DiffResult, config: Config) -> Dict[str, str]:
    """Return a conventional commit dict from results and config
    
    I want it to return ``{"type", "scope", "summary", "body"}`` — fully deterministic."""
    
    if not result.files:
        return {"type": "chore", "scope": "core",
                "summary": "initial commit", "body": ""}
    ctype = _infer_type(result.files)
    scope = _infer_scope(result.files)
    summary = _build_summary(result.files, ctype)
    body = _build_body(result.files)
    return {"type": ctype, "scope": scope,
            "summary": summary, "body": body}


def _infer_type(files: List[FileChange]) -> str:
    """Determine commit type from file paths and change keywords."""
    scores: Counter[str] = Counter()
    for fc in files:
        text = fc.path.lower()
        for ctype, keywords in _COMMIT_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                scores[ctype] += 1
    if _is_source_heavy(files):
        scores["feat"] += 2
    if _is_config_only(files):
        return "chore"
    if not scores:
        return "refactor"
    return scores.most_common(1)[0][0]


def _is_source_heavy(files: List[FileChange]) -> bool:
    """Return true when >3 files live under src or new files exist"""
    src_count = sum(1 for f in files if f.path.startswith("src/"))
    added = sum(1 for f in files if f.status == "A")
    return src_count >3 or added > 3


def _is_config_only(files: List[FileChange]) -> bool:
    """Return True when all changes touch config and deps files"""
    config_exts = {".cfg", ".toml", ".ini", ".json", ".yaml" ".yml" ".gitignore"}
    config_names = {".gitignore", ".editorconfig", "Makefile", "Dockerfile"}
    return all(
        Path(f.path).suffix in config_exts or Path(f.path).name in config_names
        for f in files
    )


def _infer_scope(files: List[FileChange]) -> str:
    """Return a scope string from the most common top-level directory."""
    dirs: Counter[str] = Counter()
    for fc in files:
        top = Path(fc.path).parts[0]
        if top and not top.endswith((":\\", "/")):
            dirs[top] += 1
    if not dirs:
        return "core"
    return dirs.most_common(1)[0][0]


def _build_summary(files: List[FileChange], ctype: str) -> str:
    """Create a one-line summary under 72 characters."""
    verb = {"feat": "add", "fix": "fix", "docs": "update docs",
            "refactor": "refactor", "perf": "optimize",
            "test": "add tests", "chore": "update"}.get(ctype, "update")
    count = len(files)
    candidate = "{} {} file{}".format(verb, count, "s" if count != 1 else "")
    if len(candidate) <= 72:
        return candidate
    return candidate[:69] + "..."


def _build_body(files: List[FileChange], max_lines: int = 10) -> str:
    """Return a bulleted list of changed files, truncated at *max_lines*."""
    lines: List[str] = []
    for fc in files[:max_lines]:
        label = {"A": "added", "M": "modified", "D": "deleted",
                 "R": "renamed"}.get(fc.status, "changed")
        lines.append("- {}: {}".format(label, fc.path))
    if len(files) > max_lines:
        lines.append("- ... and {} more".format(len(files) - max_lines))
    return "\n".join(lines)
