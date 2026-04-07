import tempfile
"""Tests for commitforge.parser module — stdlib unittest only."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from commitforge.parser import parse_diff, _parse_numstat
from commitforge.types import DiffResult, FileChange


def _make_mock(stdout: str, returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


class TestParser(unittest.TestCase):

    def test_parse_diff_basic(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        numstat = "10\t5\tsrc/main.py\n3\t0\tREADME.md\n"
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [_make_mock("main"), _make_mock(numstat)]
            result = parse_diff(d)
        self.assertIsInstance(result, DiffResult)
        self.assertEqual(len(result.files), 2)
        self.assertEqual(result.total_additions, 13)
        self.assertEqual(result.total_deletions, 5)

    def test_parse_diff_empty_repo(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [_make_mock(""), _make_mock("")]
            result = parse_diff(d)
        self.assertEqual(result.files, [])
        self.assertEqual(result.total_additions, 0)

    def test_parse_diff_non_git(self) -> None:
        result = parse_diff(Path(tempfile.mkdtemp()))
        self.assertIsInstance(result, DiffResult)
        self.assertEqual(result.files, [])

    def test_parse_diff_detached_head(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [_make_mock(""), _make_mock("")]
            result = parse_diff(d)
        self.assertEqual(result.branch, "(detached)")

    def test_parse_numstat_with_renames(self) -> None:
        lines = ["-\t-\told_name.py\tnew_name.py"]
        changes = _parse_numstat(lines)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "R")

    def test_parse_numstat_ignore_filter(self) -> None:
        lines = ["5\t0\tnode_modules/pkg.js\n10\t3\tsrc/app.py"]
        changes = _parse_numstat(lines, {"ignore": ["node_modules/*"]})
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].path, "src/app.py")

    def test_parse_diff_git_not_found(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = parse_diff(d)
        self.assertIsInstance(result, DiffResult)
