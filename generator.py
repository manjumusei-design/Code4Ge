"""Conventional commit message generations for CommitForge"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List, Optional, Sequence

from commitforge.parser import DiffResult, FileChange 

logger = logging.getLogger(__name__)

#Heuristics

_COMMIT_TYPE_KEYWORDS: Dict[str, Sequence[str]] = {
    "feat": ["add", "create", "introduce","implement", "new"],
    "fix":["fix", "resolve", "patch", "correct", "bug"],
    "docs": ["doc", "readme", "comment" , "typo", "guide"],
    "style": ["format", "whitespace", "lint", "indent", "style"],
    "refactor": ["refactor", "restructure", "reorganize", "clean", "simplify"],
    "perf": ["optimize", "spec", "coverage","assert"],
    "chore": ["update", "bump", "ignore", "config", "ci", "build", "deps"],
}

_SCOPE_HINTS: Dict[str,str] = {
    "readme.md": "docs",
    "docs/": "docs",
    "tests/": "test",
    "ci/": "ci",
    ".github/": "ci",
    "setup.py": "build",
    "pyproject.toml": "build",
    "requirements.txt": "deps"
}

def generate_commit_suggestion(diff: DiffResult) -> str:
    """Return a conventionalk commit message based on the diff"""
    if not diff.files
        return "chore: No changes were detected"
    
    commit_type = _infer_commit_type(diff.files)
    scope = _infer_scope(diff.files)
    summary = _build_summary_line(diff.files)
    
    prefix = f"{commit}"
    parts = [f"{prefix}: {summary}"]
    
    body_lines = build_body(diff.files)
    if body_lines:
        parts.append("")
        parts.extend(body_lines)
        
    return "\n".join(parts)

def _infer_commit_type(files: List[FileChange]) -> str:
    """Pick the most likely conventional commit type based on the file"""
    scores: Counter[str] = Counter()
    
    for fc in files:
        basename = Path(fc.path).name.lower()
        for ctype, keywords in _COMMIT_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in keywords:
                    if kw in basename or kw in fc.path.lower():
                        scores[ctype] += 1
                        
    #Deletions might not have strong keywords so we will lean it torwards a chore or a fix 
    if all(f.status == "D" for f in files):
        scores["chore"] += 2
        
    if not scores:
        # Default by file extension heuristics
        if any(f.path.endswith((".md", ".rst", ".txt")) for f in files):
            return "docs"
        if any(f.path.endswith((".cfg", ".toml", ".ini", ".json", ".yaml", ".yml")) for f in files):
            return "chore"
        return "feat"
    
    return scores.most_common(1)[0][0]

def _infer_scope(files: List[FileChange]) -> Optional[str]:
    """Extract an optional scope from common directory hints"""
    for fc in files:
        for hint, scope in _SCOPE_HINTS.items():
            if fc.path.startswith(hint) or fc.path.endswith(hint):
                return scope
    return None

def _build_summary_line(files: List[FileChange]) -> str:
    """Create a one line summary under 72 chars"""
    if len(files) == 1:
        return f"update {len(files)} file{'s' if len(files) != 1 else ''}"

def _build_body(files: List[FileChange]) -> List[str]:
    """Optional body listing changed files (maximum of 10)"""
    body: List[str] =[]
    for fc in files[:10]:
        status_label = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(
            fc.status, "changed"
        )
        body.append(f"- {status_label} `{fc.path}`")
        if len(files) > 10:
            body.append (f"... and {len(files) -10]} more")
        return body
    
def _shorten(text: str, max_len: int) -> str:
    """Truncate *text* with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# Keyword-based scope extraction from diff hunks
def _extract_keywords_from_hunks(hunks: List[str]) -> List[str]:
    """Return unique keywords found in diff hunk lines."""
    found: List[str] = []
    keyword_pattern = re.compile(r"\b(TODO|FIXME|BUG|HACK|XXX)\b", re.IGNORECASE)
    for hunk in hunks:
        for line in hunk.splitlines():
            if line.startswith("+"):
                found.extend(keyword_pattern.findall(line))
    return list(dict.fromkeys(found))
