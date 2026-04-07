"""Git diff parser for CommitForge."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from commitforge.types import DiffResult, FileChange
from commitforge.utils import detect_repo_root, log

logger = logging.getLogger(__name__)
_GIT_TIMEOUT = 30


def _run_git(repo_root: Path, *args: str) -> Optional[str]:
    """Run a git command; return stdout or None on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root)] + list(args),
            capture_output=True, text=True, check=True,
            timeout=_GIT_TIMEOUT,
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.debug("git %s failed: %s", " ".join(args), exc)
        return None
    except FileNotFoundError:
        log("git not found in PATH", logging.WARNING)
        return None


def parse_diff(repo_root: Path,
               filters: Optional[Dict[str, Any]] = None) -> DiffResult:
    """Parse ``git diff --numstat`` into a structured DiffResult.

    Applies optional filters cuz (``{"since": str, "author": str,
    "ignore": [str]}``).  Returns empty DiffResult on any git error.
    """
    resolved = detect_repo_root(repo_root)
    if resolved is None:
        log("Not a Git repository: {}".format(repo_root), logging.ERROR)
        return DiffResult(repo_root=str(repo_root))

    branch = _detect_branch(resolved)
    base_ref = _resolve_base(resolved, filters)
    raw = _run_git(resolved, "diff", "--numstat", base_ref)
    if raw is None:
        log("No diff data for base={}".format(base_ref), logging.WARNING)
        return DiffResult(branch=branch, repo_root=str(resolved))

    changes = _parse_numstat(raw.strip().splitlines(), filters)
    additions = sum(c.additions for c in changes)
    deletions = sum(c.deletions for c in changes)
    return DiffResult(
        branch=branch, files=changes,
        total_additions=additions, total_deletions=deletions,
        repo_root=str(resolved),
    )


def _detect_branch(repo_root: Path) -> str:
    """Return current branch name, or ``"(detached)"`` if HEAD is detached."""
    out = _run_git(repo_root, "branch", "--show-current")
    return out.strip() if out and out.strip() else "(detached)"


def _resolve_base(repo_root: Path,
                  filters: Optional[Dict[str, Any]]) -> str:
    """Determine the diff base ref, defaulting to ``HEAD``."""
    if not filters:
        return "HEAD"
    if filters.get("since"):
        from commitforge.filters import apply_since
        if not apply_since(repo_root, filters["since"]):
            log("No commits since {}; using HEAD".format(filters["since"]),
                logging.WARNING)
            return "HEAD"
    if filters.get("author"):
        from commitforge.filters import apply_author
        if not apply_author(repo_root, filters["author"]):
            log("No commits by {}; using HEAD".format(filters["author"]),
                logging.WARNING)
            return "HEAD"
    return "HEAD"


def _parse_numstat(lines: List[str],
                   filters: Optional[Dict[str, Any]] = None) -> List[FileChange]:
    """Convert numstat output lines into FileChange objects."""
    changes: List[FileChange] = []
    ignore_patterns = filters.get("ignore", []) if filters else []
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add, delete, path = parts
        if _should_skip(path, ignore_patterns):
            continue
        additions = _safe_int(add)
        deletions = _safe_int(delete)
        status = "R" if add == "-" else _guess_status(additions, deletions)
        changes.append(FileChange(
            path=path, additions=additions,
            deletions=deletions, status=status,
        ))
    return changes


def _safe_int(value: str) -> int:
    """Convert to int; return 0 for binary markers (``-``)."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _guess_status(additions: int, deletions: int) -> str:
    """Infer change status from numeric diff stats."""
    if additions == 0 and deletions > 0:
        return "D"
    if additions > 0 and deletions == 0:
        return "A"
    return "M"


def _should_skip(path: str, ignore_patterns: List[str]) -> bool:
    """Return True if *path* matches any ignore pattern."""
    from commitforge.filters import apply_ignore
    from pathlib import Path as _P
    return any(apply_ignore(_P(path), [pat]) for pat in ignore_patterns)
