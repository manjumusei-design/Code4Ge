"""Shared pytest fixtures for commitforge tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commitforge.types import Config


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary directory with a .git folder."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return tmp_path


@pytest.fixture
def mock_config() -> Config:
    """Return a standard Config for tests."""
    return Config()


@pytest.fixture
def mock_git_ls_files():
    """Context manager that mocks git ls-files output."""

    def _mock(output: str, returncode: int = 0):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = output
        mock.stderr = ""
        return patch("subprocess.run", return_value=mock)

    return _mock


@pytest.fixture
def mock_git_diff():
    """Context manager that mocks git diff --name-status HEAD."""

    def _mock(output: str, returncode: int = 0):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = output
        mock.stderr = ""
        return patch("subprocess.run", return_value=mock)

    return _mock
