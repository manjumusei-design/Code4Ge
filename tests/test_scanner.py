import tempfile
"""Tests for commitforge.scanner module — stdlib unittest only."""

import unittest
from pathlib import Path

from commitforge.scanner import (
    scan_large_files, scan_binaries, scan_todos_fixmes,
    scan_missing_docstrings, scan_unused_imports, _find_unused,
)
from commitforge.types import Config


def _make_config(**kw: dict) -> Config:
    defaults: dict = {"max_file_size_mb": 0.0001}
    defaults.update(kw)
    return Config(**defaults)  # type: ignore[arg-type]


class TestScanner(unittest.TestCase):

    def test_scan_large_files(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "big.py").write_text("x = " + "A" * 1000)
        issues = scan_large_files(d, _make_config())
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, "large-file")

    def test_scan_large_files_below_limit(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "small.py").write_text("x = 1")
        issues = scan_large_files(d, _make_config(max_file_size_mb=1.0))
        self.assertEqual(len(issues), 0)

    def test_scan_binaries(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "data.bin").write_bytes(b"\x89PNG\x00\x00\x00")
        issues = scan_binaries(d, [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, "binary-file")

    def test_scan_binaries_text_file(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "readme.txt").write_text("Hello world")
        issues = scan_binaries(d, [])
        self.assertEqual(len(issues), 0)

    def test_scan_todos_excessive(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "messy.py").write_text(
            "# TODO 1\n# TODO 2\n# FIXME 3\n# HACK 4\n# BUG 5\n"
        )
        issues = scan_todos_fixmes(d, [])
        self.assertEqual(len(issues), 1)
        self.assertIn("5", issues[0].message)

    def test_scan_todos_below_threshold(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "clean.py").write_text("# TODO one\n")
        issues = scan_todos_fixmes(d, [])
        self.assertEqual(len(issues), 0)

    def test_scan_missing_docstrings(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "nodoc.py").write_text("def foo():\n    pass\n")
        issues = scan_missing_docstrings(d, [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, "missing-docstring")

    def test_scan_docstrings_present(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "good.py").write_text('def foo():\n    """Nice."""\n    pass\n')
        issues = scan_missing_docstrings(d, [])
        self.assertEqual(len(issues), 0)

    def test_scan_unused_imports(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / "unused.py").write_text("import os\nimport sys\nprint(sys.path)\n")
        issues = scan_unused_imports(d, [])
        unused_names = {i.message.split("'")[1] for i in issues}
        self.assertIn("os", unused_names)

    def test_scan_ignore_paths_skipped(self) -> None:
        d = Path(tempfile.mkdtemp())
        vend = d / "node_modules"
        vend.mkdir()
        (vend / "big.py").write_text("x = " + "B" * 1000)
        issues = scan_large_files(d, _make_config())
        self.assertEqual(len(issues), 0)

    def test_find_unused_empty(self) -> None:
        self.assertEqual(_find_unused("x = 1\n"), [])
