import sqlite3
import tempfile
import unittest
from pathlib import Path

from rock_paper_scissors.game import Match, Move
from rock_paper_scissors.storage import HistoryStore, StorageError


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "history.sqlite3"
        self.store = HistoryStore(self.path)
        self.match = Match()
        self.match.play(Move.ROCK, Move.SCISSORS)
        self.match.play(Move.ROCK, Move.SCISSORS)

    def test_missing_history_is_read_without_creating_file(self):
        self.assertEqual(self.store.load(), [])
        self.assertFalse(self.path.exists())

    def test_finished_match_round_trip_and_idempotent_save(self):
        self.store.save("match-1", "Ada", self.match)
        self.store.save("match-1", "Ada", self.match)
        records = self.store.load()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["player"], "Ada")
        self.assertEqual((records[0]["wins"], records[0]["outcome"]), (2, "win"))
        self.assertTrue(records[0]["finished_at"].endswith("+00:00"))

    def test_names_are_bound_as_sql_parameters(self):
        name = "'; DROP TABLE matches;--"
        self.store.save("match-1", name, self.match)
        self.assertEqual(self.store.load()[0]["player"], name)

    def test_unfinished_and_empty_sessions_are_not_saved(self):
        for match in (Match(), Match(None)):
            with self.assertRaises(ValueError):
                self.store.save("match-1", "Ada", match)
            match.finish()
            with self.assertRaises(ValueError):
                self.store.save("match-1", "Ada", match)

    def test_corrupt_database_is_preserved(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b"This is not SQLite.")
        with self.assertRaises(StorageError):
            self.store.save("match-1", "Ada", self.match)
        self.assertEqual(self.path.read_bytes(), b"This is not SQLite.")

    def test_unknown_version_is_preserved(self):
        self.path.parent.mkdir()
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 9")
        with self.assertRaises(StorageError):
            self.store.save("match-1", "Ada", self.match)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 9)

    def test_existing_unrelated_database_is_not_modified(self):
        self.path.parent.mkdir()
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE notes (content TEXT)")
            connection.execute("INSERT INTO notes VALUES ('keep me')")
        with self.assertRaises(StorageError):
            self.store.load()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(
                connection.execute("SELECT content FROM notes").fetchone()[0], "keep me"
            )
