"""Tests for commitforge.config module — stdlib unittest only."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from commitforge.config import (
    load_config, create_default_config, validate_config,
)
from commitforge.types import Config


class TestConfig(unittest.TestCase):

    def test_load_config_defaults(self) -> None:
        cfg = load_config(Path(tempfile.mkdtemp()))
        self.assertIsInstance(cfg, Config)
        self.assertEqual(cfg.max_file_size_mb, 0.5)
        self.assertIn("node_modules", cfg.ignore_paths)

    def test_load_config_merges_user(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".commitforge.json").write_text(json.dumps({"max_file_size_mb": 2.0}))
        cfg = load_config(d)
        self.assertEqual(cfg.max_file_size_mb, 2.0)
        self.assertIn("node_modules", cfg.ignore_paths)

    def test_load_config_missing_file(self) -> None:
        cfg = load_config(Path(tempfile.mkdtemp()))
        self.assertEqual(cfg.max_file_size_mb, 0.5)

    def test_load_config_invalid_json(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".commitforge.json").write_text("{not json")
        cfg = load_config(d)
        self.assertEqual(cfg.max_file_size_mb, 0.5)

    def test_load_config_permission_error(self) -> None:
        d = Path(tempfile.mkdtemp())
        (d / ".commitforge.json").write_text("{}")
        with patch("builtins.open", side_effect=PermissionError):
            cfg = load_config(d)
        self.assertIsInstance(cfg, Config)

    def test_create_default_config(self) -> None:
        d = Path(tempfile.mkdtemp())
        create_default_config(d)
        out = d / ".commitforge.json"
        self.assertTrue(out.exists())
        data = json.loads(out.read_text())
        self.assertEqual(data["max_file_size_mb"], 0.5)

    def test_create_default_config_no_overwrite(self) -> None:
        d = Path(tempfile.mkdtemp())
        cfg_file = d / ".commitforge.json"
        cfg_file.write_text('{"custom": true}')
        create_default_config(d)
        self.assertEqual(json.loads(cfg_file.read_text()), {"custom": True})

    def test_validate_config_type_coercion(self) -> None:
        raw: dict = {"max_file_size_mb": "not_a_number", "ignore_paths": "also_bad"}
        cfg = validate_config(raw)
        self.assertEqual(cfg.max_file_size_mb, 0.5)
        self.assertIsInstance(cfg.ignore_paths, list)
