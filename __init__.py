__version__ = "0.1.0"

DEFAULT_CONFIG = {
    "ignored_paths": ["node_modules",".git",".venv", "__pycache__","dist","build"],
    "max_file_size_kb": 500,
    "severity_threshholds": {"warning":3, "critical":10},
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