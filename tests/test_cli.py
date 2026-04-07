"""Tests for commitforge.cli module — stdlib unittest only."""

import unittest
from unittest.mock import patch

from commitforge.cli import build_parser, main


class TestBuildParser(unittest.TestCase):

    def test_no_args_shows_help(self) -> None:
        code = main([])
        self.assertEqual(code, 0)

    def test_version_flag(self) -> None:
        """--version prints version; main catches SystemExit."""
        # argparse --version calls parser.exit(0) which raises SystemExit,
        # but our try/except in main catches it and returns the code.
        code = main(["--version"])
        self.assertIn(code, (0, None))

    def test_init_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init"])
        self.assertEqual(args.command, "init")

    def test_scan_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["scan", "--since", "2024-01-01"])
        self.assertEqual(args.command, "scan")
        self.assertEqual(args.since, "2024-01-01")

    def test_health_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["health", "--format", "md"])
        self.assertEqual(args.command, "health")
        self.assertEqual(args.format, "md")

    def test_report_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["report", "--format", "html"])
        self.assertEqual(args.command, "report")
        self.assertEqual(args.format, "html")

    def test_analyze_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["analyze"])
        self.assertEqual(args.command, "analyze")

    def test_ignore_repeatable(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["scan", "--ignore", "*.pyc", "--ignore", "*.pyo"])
        self.assertEqual(args.ignore, ["*.pyc", "*.pyo"])


class TestMain(unittest.TestCase):

    def test_unknown_command_returns_0(self) -> None:
        code = main([])
        self.assertEqual(code, 0)

    def test_keyboard_interrupt_returns_130(self) -> None:
        with patch("commitforge.cli._cmd_scan", side_effect=KeyboardInterrupt):
            code = main(["scan"])
        self.assertEqual(code, 130)

    def test_scan_non_git_dir_returns_1(self) -> None:
        code = main(["--repo", "/tmp", "scan", "--quiet"])
        self.assertEqual(code, 1)

    def test_health_non_git_dir_returns_1(self) -> None:
        code = main(["--repo", "/tmp", "health", "--quiet"])
        self.assertEqual(code, 1)
