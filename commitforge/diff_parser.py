"""Parse git diff output to extract meaningful change descriptions."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from commitforge.utils import _log, format_error

import logging

_PY_FUNC_RE = re.compile(r"^(?:def|async def)\s+(\w+)\s*\(")
_PY_CLASS_RE = re.compile(r"^class\s+(\w+)")
_PY_IMPORT_RE = re.compile(r"^(?:import|from)\s+(\w+)")
_JS_FUNC_RE = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(")
_JS_CONST_RE = re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=")
_JS_IMPORT_RE = re.compile(r"^(?:import|require)\s*[\(\{]?\s*(\w+)")

_CHANGE_TYPES = {
    "A": "Added",
    "M": "Modified",
    "D": "Deleted",
    "R": "Renamed",
}


@dataclass
class DiffChange:
    """A single meaningful change extracted from a diff hunk."""

    path: str
    change_type: str  # "added", "removed", "modified"
    kind: str  # "function", "class", "import", "line", "block"
    name: str  # function/class name or description
    line_number: int = 0
    details: str = ""


@dataclass
class FileDiff:
    """All changes extracted for a single file."""

    path: str
    status: str  # A, M, D, R
    changes: List[DiffChange] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0


def parse_diff(repo_root: Path) -> List[FileDiff]:
    """Run git diff and parse the output into structured FileDiff objects.

    Args:
        repo_root: Path to the repository root.

    Returns:
        List of FileDiff objects, one per changed file.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--unified=0"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        _log(format_error(exc, "git diff"), logging.ERROR)
        return []

    if not result.stdout.strip():
        return []

    return _parse_diff_text(result.stdout)


def _parse_diff_text(text: str) -> List[FileDiff]:
    """Parse raw diff text into FileDiff objects.

    Args:
        text: Raw output from git diff.

    Returns:
        List of FileDiff objects.
    """
    files: dict[str, FileDiff] = {}
    current_file: FileDiff | None = None
    current_hunk_start = 0

    for line in text.splitlines():
        # File header: diff --git a/path b/path
        header = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if header:
            path = header.group(2)
            current_file = FileDiff(path=path, status="M")
            files[path] = current_file
            continue

        # Status line: old mode / new mode / index / --- / +++
        if line.startswith("--- ") or line.startswith("+++ ") or line.startswith("index "):
            continue
        if line.startswith("old mode") or line.startswith("new mode"):
            continue

        # New file: +++ b/path
        new_file = re.match(r"^\+\+\+ b/(.+)$", line)
        if new_file and current_file is None:
            path = new_file.group(1)
            current_file = FileDiff(path=path, status="A")
            files[path] = current_file
            continue

        # Deleted file: --- a/path followed by no +++ line
        del_file = re.match(r"^--- a/(.+)$", line)
        if del_file and current_file is None:
            path = del_file.group(1)
            current_file = FileDiff(path=path, status="D")
            files[path] = current_file
            continue

        # Hunk header: @@ -old,start +new,start @@
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            current_hunk_start = int(hunk.group(1))
            continue

        if current_file is None:
            continue

        # Added line
        if line.startswith("+") and not line.startswith("+++"):
            current_file.added_lines += 1
            change = _classify_added_line(line[1:], current_file.path, current_hunk_start)
            if change:
                current_file.changes.append(change)
                current_hunk_start += 1

        # Removed line
        elif line.startswith("-") and not line.startswith("---"):
            current_file.removed_lines += 1
            change = _classify_removed_line(line[1:], current_file.path, current_hunk_start)
            if change:
                current_file.changes.append(change)

    # Post-process: detect new files (no --- line means status A)
    for path, fdiff in files.items():
        if fdiff.added_lines > 0 and fdiff.removed_lines == 0:
            fdiff.status = "A"
        elif fdiff.added_lines == 0 and fdiff.removed_lines > 0:
            fdiff.status = "D"

    return list(files.values())


def _classify_added_line(line: str, path: str, line_num: int) -> DiffChange | None:
    """Classify an added line and return a DiffChange if meaningful.

    Args:
        line: The line content (without + prefix).
        path: File path.
        line_num: Line number in the new file.

    Returns:
        DiffChange if the line is meaningful, None otherwise.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    ext = Path(path).suffix.lower()

    if ext == ".py":
        func = _PY_FUNC_RE.match(stripped)
        if func:
            return DiffChange(
                path=path,
                change_type="added",
                kind="function",
                name=func.group(1),
                line_number=line_num,
                details=f"Added function `{func.group(1)}()`",
            )
        cls = _PY_CLASS_RE.match(stripped)
        if cls:
            return DiffChange(
                path=path,
                change_type="added",
                kind="class",
                name=cls.group(1),
                line_number=line_num,
                details=f"Added class `{cls.group(1)}`",
            )
        imp = _PY_IMPORT_RE.match(stripped)
        if imp:
            return DiffChange(
                path=path,
                change_type="added",
                kind="import",
                name=imp.group(1),
                line_number=line_num,
                details=f"Added import `{imp.group(1)}`",
            )

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        func = _JS_FUNC_RE.match(stripped)
        if func:
            return DiffChange(
                path=path,
                change_type="added",
                kind="function",
                name=func.group(1),
                line_number=line_num,
                details=f"Added function `{func.group(1)}()`",
            )
        const = _JS_CONST_RE.match(stripped)
        if const:
            return DiffChange(
                path=path,
                change_type="added",
                kind="variable",
                name=const.group(1),
                line_number=line_num,
                details=f"Added variable `{const.group(1)}`",
            )
        imp = _JS_IMPORT_RE.match(stripped)
        if imp:
            return DiffChange(
                path=path,
                change_type="added",
                kind="import",
                name=imp.group(1),
                line_number=line_num,
                details=f"Added import `{imp.group(1)}`",
            )

    return None


def _classify_removed_line(line: str, path: str, line_num: int) -> DiffChange | None:
    """Classify a removed line and return a DiffChange if meaningful.

    Args:
        line: The line content (without - prefix).
        path: File path.
        line_num: Line number in the old file.

    Returns:
        DiffChange if the line is meaningful, None otherwise.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    ext = Path(path).suffix.lower()

    if ext == ".py":
        func = _PY_FUNC_RE.match(stripped)
        if func:
            return DiffChange(
                path=path,
                change_type="removed",
                kind="function",
                name=func.group(1),
                line_number=line_num,
                details=f"Removed function `{func.group(1)}()`",
            )
        cls = _PY_CLASS_RE.match(stripped)
        if cls:
            return DiffChange(
                path=path,
                change_type="removed",
                kind="class",
                name=cls.group(1),
                line_number=line_num,
                details=f"Removed class `{cls.group(1)}`",
            )
        imp = _PY_IMPORT_RE.match(stripped)
        if imp:
            return DiffChange(
                path=path,
                change_type="removed",
                kind="import",
                name=imp.group(1),
                line_number=line_num,
                details=f"Removed import `{imp.group(1)}`",
            )

    return None


def summarize_changes(file_diffs: List[FileDiff]) -> List[str]:
    """Generate human-readable summaries for a list of FileDiff objects.

    Args:
        file_diffs: List of FileDiff objects from parse_diff.

    Returns:
        List of summary strings, one per changed file.
    """
    summaries: List[str] = []
    for fdiff in file_diffs:
        status_label = _CHANGE_TYPES.get(fdiff.status, fdiff.status)

        if fdiff.changes:
            for change in fdiff.changes:
                summaries.append(f"{fdiff.path}: {change.details}")
        else:
            total = fdiff.added_lines + fdiff.removed_lines
            if total == 0:
                summaries.append(f"{fdiff.path}: {status_label}")
            elif total <= 5:
                summaries.append(
                    f"{fdiff.path}: {status_label} ({total} line{'s' if total != 1 else ''} changed)"
                )
            else:
                summaries.append(
                    f"{fdiff.path}: {status_label} ({fdiff.added_lines} added, "
                    f"{fdiff.removed_lines} removed)"
                )

    return summaries
