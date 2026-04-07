"""Typed data models for commitforge."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """Repository analysis configuration."""

    ignore_paths: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            ".venv",
            "__pycache__",
            "dist",
            "build",
        ]
    )
    max_file_size_mb: float = 0.5
    severity_thresholds: dict[str, int] = field(
        default_factory=lambda: {"warning": 3, "critical": 1}
    )
    commit_mappings: dict[str, str] = field(
        default_factory=lambda: {
            "test": "test",
            "docs": "docs",
            "style": "style",
            "refactor": "refactor",
            "perf": "perf",
            "chore": "chore",
        }
    )


@dataclass(frozen=True)
class Finding:
    """A single code-health or rule-violation finding."""

    path: str
    severity: str  # "info", "warning", "critical"
    type: str
    message: str


@dataclass
class ScanResult:
    """Aggregated result of a repository scan."""

    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    thresholds_exceeded: bool = False


@dataclass(frozen=True)
class CommitSuggestion:
    """A suggested conventional commit message."""

    type: str
    scope: str | None
    description: str
    breaking: bool = False
