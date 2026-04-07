import tempfile
"""Integration tests: full pipeline end-to-end — stdlib unittest only."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from commitforge.cli import main
from commitforge.config import create_default_config, load_config
from commitforge.generator import suggest_commit
from commitforge.parser import parse_diff
from commitforge.report import render_markdown, render_html


def _mock_git(stdout: str) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m


class TestIntegration(unittest.TestCase):

    def test_full_scan_pipeline(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        create_default_config(d)
        numstat = "5\t0\tsrc/main.py\n3\t1\ttests/test_main.py\n"
        with patch("subprocess.run", return_value=_mock_git(numstat)):
            code = main(["--repo", str(d), "scan", "--quiet"])
        self.assertEqual(code, 0)

    def test_full_health_pipeline(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        create_default_config(d)
        (d / "messy.py").write_text(
            "# TODO 1\n# TODO 2\n# TODO 3\n# TODO 4\n# TODO 5\n"
        )
        code = main(["--repo", str(d), "health", "--format", "text"])
        self.assertEqual(code, 0)

    def test_full_report_pipeline(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        create_default_config(d)
        with patch("subprocess.run", return_value=_mock_git("5\t0\tsrc/app.py")):
            code = main([
                "--repo", str(d), "report",
                "--format", "md", "--quiet",
            ])
        self.assertEqual(code, 0)

    def test_full_analyze_pipeline(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        create_default_config(d)
        (d / "src").mkdir()
        (d / "src" / "app.py").write_text("def run(): pass\n")
        with patch("subprocess.run", return_value=_mock_git("10\t0\tsrc/app.py")):
            code = main([
                "--repo", str(d), "analyze",
                "--format", "text", "--quiet",
            ])
        self.assertEqual(code, 0)

    def test_config_load_scan_cycle(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".git").mkdir()
        create_default_config(d)
        cfg = load_config(d)
        self.assertEqual(cfg.max_file_size_mb, 0.5)
        with patch("subprocess.run", return_value=_mock_git("")):
            result = parse_diff(d)
        commit = suggest_commit(result, cfg)
        self.assertIn("type", commit)
        self.assertIn("summary", commit)

    def test_report_render_all_formats(self) -> None:
        commit = {
            "type": "feat", "scope": "api",
            "summary": "add endpoint", "body": "- added /users",
        }
        md = render_markdown(commit, [])
        self.assertIn("# CommitForge", md)
        html = render_html(commit, [])
        self.assertIn("<!DOCTYPE html>", html)
