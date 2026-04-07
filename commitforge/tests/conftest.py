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


@pytest.fixture
def mock_git_commands():
    """Fixture that mocks all git subprocess calls with realistic outputs.

    Usage:
        def test_something(mock_git_commands):
            mock_git_commands.configure(
                ls_files="src/app.py\ntests/test_app.py\n",
                diff="M\tsrc/app.py\nA\ttests/test_app.py\n",
                status="",
            )
    """

    class MockGitCommands:
        def __init__(self) -> None:
            self.ls_files_output = ""
            self.diff_output = ""
            self.status_output = ""
            self.ls_files_rc = 0
            self.diff_rc = 0
            self.status_rc = 0

        def configure(
            self,
            ls_files: str = "",
            diff: str = "",
            status: str = "",
            ls_files_rc: int = 0,
            diff_rc: int = 0,
            status_rc: int = 0,
        ) -> None:
            self.ls_files_output = ls_files
            self.diff_output = diff
            self.status_output = status
            self.ls_files_rc = ls_files_rc
            self.diff_rc = diff_rc
            self.status_rc = status_rc

        def _make_mock(
            self, output: str, returncode: int
        ) -> MagicMock:
            mock = MagicMock()
            mock.returncode = returncode
            mock.stdout = output
            mock.stderr = ""
            return mock

        def subprocess_side_effect(self, *args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "ls-files" in cmd:
                return self._make_mock(
                    self.ls_files_output, self.ls_files_rc
                )
            if isinstance(cmd, list) and "diff" in cmd:
                return self._make_mock(
                    self.diff_output, self.diff_rc
                )
            if isinstance(cmd, list) and "status" in cmd:
                return self._make_mock(
                    self.status_output, self.status_rc
                )
            raise FileNotFoundError(f"Unknown command: {cmd}")

    helper = MockGitCommands()
    with patch(
        "subprocess.run", side_effect=helper.subprocess_side_effect
    ):
        yield helper
