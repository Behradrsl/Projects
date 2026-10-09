import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from number_guesser.game import DIFFICULTIES, Game
from number_guesser.storage import Record, ScoreStore, StorageError


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "scores.json"
        self.store = ScoreStore(self.path)
        game = Game(DIFFICULTIES["normal"], secret=42)
        game.guess(42)
        self.record = Record.from_game("Ada", game)

    def test_missing_history_and_round_trip(self):
        self.assertEqual(self.store.load(), [])
        self.store.append(self.record)
        self.store.append(self.record)
        self.assertEqual(self.store.load(), [self.record, self.record])

    def test_corrupt_history_is_never_overwritten(self):
        self.path.parent.mkdir()
        for content in (
            "not json",
            '{"version": 2, "rounds": []}',
            '{"version": 1, "rounds": [{"score": 900}]}',
            '{"version": true, "rounds": []}',
            '{"version": 1, "rounds": [null]}',
        ):
            with self.subTest(content=content):
                self.path.write_text(content)
                with self.assertRaises(StorageError):
                    self.store.append(self.record)
                self.assertEqual(self.path.read_text(), content)

    def test_failed_replace_preserves_previous_history_and_cleans_temp_file(self):
        self.store.append(self.record)
        before = self.path.read_bytes()
        with patch("number_guesser.storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(StorageError):
                self.store.append(self.record)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".scores-*")), [])

    def test_invalid_record_is_rejected(self):
        self.store.append(self.record)
        raw = json.loads(self.path.read_text())
        for field, value in (
            ("score", 99),
            ("attempts", True),
            ("player", "\x1b[31m"),
            ("played_at", "2026-01-01"),
            ("difficulty", []),
        ):
            with self.subTest(field=field):
                modified = json.loads(json.dumps(raw))
                modified["rounds"][0][field] = value
                self.path.write_text(json.dumps(modified))
                with self.assertRaises(StorageError):
                    self.store.load()

    def test_unfinished_round_cannot_be_saved(self):
        with self.assertRaises(ValueError):
            Record.from_game("Ada", Game(DIFFICULTIES["normal"], secret=42))
