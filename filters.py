"""Filter helpers for commitforge diff parsing"""

from __future__ import annotations

import datetime
import fnmatch
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)
_GIT_TIMEOUT = 30


def _run_git_log(repo_root: Path, *args: str) -> Optional[str]:
    """Run ``git log`` with args; return stdout or None on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log"] + list(args),
            capture_output=True, text=True, check=True,
            timeout=_GIT_TIMEOUT,
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    
    
def apply_since(repo_root: Path, since: str) -> bool:
    """Return True if the latest commit is newer than a date specified, it also falls back to True if the date cannot be validated"""
    
    
    
    
    try:
        cutoff = datetime.datetime.strptime(since, "%Y-%m-%d")
    except ValueError:
        log_msg("Invalid --since date '{}'; ignoring filter".format(since))
        return True
    out = _run_git_log(repo_root, "--1", "--format=%ci")
    if out is None:
        return True
    commit_date= _parse_commit_date(out.strip())
    if commit_date is None:
        return True
    return commit_date >= cutoff 

def apply_author(repo_root: Path, author: str) -> bool:
    """Return True if any commit matches *author* in the repo."""
    if not author or not author.strip():
        return False
    out = _run_git_log(repo_root, "-1", "--author={}".format(author),
                       "--format=%H")
    matched = out is not None and bool(out.strip())
    if not matched:
        log_msg("No commits by '{}' found".format(author))
    return matched


def apply_ignore(file_path: Path, patterns: List[str]) -> bool:
    """Return true if the file path matches any of the glob pat terns in patterns, this function checks for filename, fullpath and directory 
    prefix matches so that patterns like node_modules also skip node_modules/foo.js"""
    
    
    
    name = file_path.name
    str_path = str(file_path)
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
        if fnmatch.fnmatch(str_path, pat):
            return True
        if str_path.startswith(pat + "/") or str_path.startswith(pat + "\\"):
            return True
    return False


def _parse_commit_date(raw: str) -> Optional[datetime.datetime]:
    """Parse a git commit date string into a datetime object."""
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def log_msg(msg: str) -> None:
    """Log a warning to the module logger"""
    logger.warning(msg)

    
    