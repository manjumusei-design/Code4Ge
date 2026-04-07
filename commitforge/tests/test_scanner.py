"""Tests for commitforge.scanner module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from commitforge.scanner import scan_repo
from commitforge.types import Config


class TestScanRepo:
    def test_basic_scan(self, tmp_repo: Path, mock_git_ls_files) -> None:
        (tmp_repo / "src").mkdir()
        (tmp_repo / "src" / "app.py").write_text("x = 1")
        (tmp_repo / "tests").mkdir()
        (tmp_repo / "tests" / "test_app.py").write_text("pass")
        with mock_git_ls_files("src/app.py\ntests/test_app.py\n"):
            result = scan_repo(tmp_repo, Config())
        assert result.files_scanned == 2

    def test_ignore_paths(self, tmp_repo: Path, mock_git_ls_files) -> None:
        (tmp_repo / "src").mkdir()
        (tmp_repo / "src" / "app.py").write_text("x = 1")
        config = Config(ignore_paths=["node_modules"])
        with mock_git_ls_files("src/app.py\nnode_modules/pkg.js\n"):
            result = scan_repo(tmp_repo, config)
        assert result.files_scanned == 1

    def test_size_filtering(self, tmp_repo: Path, mock_git_ls_files) -> None:
        big = tmp_repo / "large.bin"
        big.write_bytes(b"x" * 1000)
        config = Config(max_file_size_mb=0.0005)
        with mock_git_ls_files("large.bin\n"):
            result = scan_repo(tmp_repo, config)
        assert result.files_scanned == 0

    def test_subprocess_error(self, tmp_repo: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = scan_repo(tmp_repo, Config())
        assert result.files_scanned == 0

    def test_empty_output(self, tmp_repo: Path, mock_git_ls_files) -> None:
        with mock_git_ls_files(""):
            result = scan_repo(tmp_repo, Config())
        assert result.files_scanned == 0
