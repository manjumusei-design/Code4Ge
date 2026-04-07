"""Git-aware file discovery, ignore/size filtering."""

from __future__ import annotations

import fnmatch
import logging
import subprocess
from pathlib import Path
from typing import List

from commitforge.types import Config, ScanResult
from commitforge.utils import _log, format_error


def scan_repo(repo_root: Path, config: Config) -> ScanResult:
    """Return a ScanResult listing tracked files that pass filters.

    Filters out paths matching *config.ignore_paths* and files
    exceeding *config.max_file_size_mb*.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        _log(format_error(exc, "git ls-files"), logging.ERROR)
        return ScanResult()
    except FileNotFoundError:
        _log("git not found in PATH", logging.WARNING)
        return ScanResult()
    except OSError as exc:
        _log(format_error(exc, "subprocess error"), logging.ERROR)
        return ScanResult()

    lines = result.stdout.strip().splitlines()
    limit_bytes = int(config.max_file_size_mb * 1024 * 1024)
    files_scanned = 0

    for rel in lines:
        if _should_ignore(rel, config.ignore_paths):
            continue
        full = repo_root / rel
        try:
            size = full.stat().st_size
        except (OSError, PermissionError):
            continue
        if size > limit_bytes:
            continue
        files_scanned += 1

    return ScanResult(files_scanned=files_scanned)


def _should_ignore(rel_path: str, ignore_paths: List[str]) -> bool:
    """Return True if *rel_path* matches any glob in *ignore_paths*."""
    posix = rel_path.replace("\\", "/")
    name = Path(posix).name
    for pattern in ignore_paths:
        if fnmatch.fnmatch(posix, pattern):
            return True
        if fnmatch.fnmatch(name, pattern):
            return True
        if posix.startswith(pattern.rstrip("/*") + "/"):
            return True
    return False
