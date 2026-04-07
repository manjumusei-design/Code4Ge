"""Core data types for commitforge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FileChange:
    """Represent a single changed file with line stats."""
    path: str
    additions: int = 0
    deletions: int = 0
    status: str = "M"  # A(dded), M(odified), D(eleted), R(enamed)


@dataclass
class DiffResult:
    """Aggregated result of a git diff parse."""
    branch: str = ""
    files: List[FileChange] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    repo_root: str = ""

    def __post_init__(self) -> None:
        """Compute aggregate totals if not explicitly provided."""
        if not self.total_additions:
            self.total_additions = sum(f.additions for f in self.files)
        if not self.total_deletions:
            self.total_deletions = sum(f.deletions for f in self.files)


@dataclass
class Issue:
    """A single code-health issue detected in a file."""
    file: str
    type: str
    severity: str
    message: str
    line: Optional[int] = None


@dataclass
class Config:
    """CommitForge configuration with strict defaults."""
    ignore_paths: List[str] = field(
        default_factory=lambda: [
            "node_modules", ".git", ".venv", "__pycache__", "dist", "build",
        ])
    max_file_size_mb: float = 0.5
    severity_thresholds: Dict[str, int] = field(
        default_factory=lambda: {"warning": 3, "critical": 1})
    commit_mappings: Dict[str, str] = field(
        default_factory=lambda: {
            "test": "test", "docs": "docs", "style": "style",
            "refactor": "refactor", "perf": "perf", "chore": "chore",
        })
