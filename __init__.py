"""CommitForge -- Offline CLI for semantic commit suggestions and repo health checks."""

__version__ = "0.1.0"

DEFAULT_CONFIG = {
    "ignored_paths": ["node_modules", ".git", ".venv", "__pycache__", "dist", "build"],
    "max_file_size_mb": 0.5,
    "severity_thresholds": {"warning": 3, "critical": 1},
    "commit_type_mappings": {
        "test": "test",
        "docs": "docs",
        "style": "style",
        "refactor": "refactor",
        "perf": "perf",
        "chore": "chore",
    },
    "ignored_patterns": ["*.pyc", "*.pyo", "*.so", "*.dll"],
}