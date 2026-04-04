"""Git diff/log parsing and change categorisation for CommitForge."""

from __future__ import annotations

    import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represent a single changed file with metadata."""

    path: str
    status: str  # A(dded), M(odified), D(eleted), R(enamed)
    insertions: int = 0
    deletions: int = 0
    hunks: List[str] = field(default_factory=list)


@dataclass
class DiffResult:
    """Container for parsed git diff output."""

    branch: str = ""
    files: List[FileChange] = field(default_factory=list)
    error: Optional[str] = None


def _run_git(cwd: Path, *args: str) -> str:
    """Run a git command safely; return stdout or raise."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout


def detect_repo_root(cwd: Path) -> Optional[Path]:
    """Walk up from *cwd* until a .git directory is found."""
    current = cwd.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def get_current_branch(repo_root: Path) -> str:
    """Return the current branch name or 'HEAD' if detached."""
    try:
        return _run_git(repo_root, "branch", "--show-current").strip() or "HEAD"
    except subprocess.CalledProcessError:
        return "HEAD"


def parse_diff_staged(repo_root: Path) -> DiffResult:
    """Parse staged changes (git diff --cached)."""
    return _parse_diff(repo_root, "HEAD")


def parse_diff_unstaged(repo_root: Path) -> DiffResult:
    """Parse unstaged changes (git diff HEAD)."""
    return _parse_diff(repo_root, "HEAD")


def parse_diff_working(repo_root: Path) -> DiffResult:
    """Parse all working-tree changes (git diff HEAD + untracked)."""
    result = _parse_diff(repo_root, "HEAD")
    _add_untracked_files(repo_root, result)
    return result


def _parse_diff(repo_root: Path, base: str) -> DiffResult:
    """Run git diff against *base* and return structured result."""
    diff_result = DiffResult()
    diff_result.branch = get_current_branch(repo_root)

    try:
        summary = _run_git(
            repo_root, "diff", "--numstat", "--diff-filter=ACMRD", base
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        diff_result.error = str(exc)
        logger.warning("git diff failed: %s", exc)
        return diff_result

    for line in summary.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ins, dels, filepath = parts
        status = _guess_status_from_numstat(ins, dels)
        diff_result.files.append(
            FileChange(
                path=filepath,
                status=status,
                insertions=_safe_int(ins),
                deletions=_safe_int(dels),
            )
        )

    return diff_result


def _add_untracked_files(repo_root: Path, result: DiffResult) -> None:
    """Append untracked files to *result.files*."""
    try:
        output = _run_git(repo_root, "ls-files", "--others", "--exclude-standard")
        for line in output.splitlines():
            if line.strip():
                result.files.append(FileChange(path=line.strip(), status="A"))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to list untracked files: %s", exc)


def _guess_status_from_numstat(ins: str, dels: str) -> str:
    """Infer A/M/D status from numstat fields."""
    if ins == "-" and dels == "-":
        return "R"  # binary / rename
    if dels == "0":
        return "A"
    if ins == "0":
        return "D"
    return "M"


def _safe_int(value: str) -> int:
    """Convert to int, returning 0 on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def get_recent_commits(repo_root: Path, count: int = 10) -> List[str]:
    """Return the last *count* commit subjects."""
    try:
        output = _run_git(
            repo_root, "log", f"-{count}", "--format=%s"
        )
        return [line.strip() for line in output.splitlines() if line.strip()]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to get recent commits: %s", exc)
        return []
