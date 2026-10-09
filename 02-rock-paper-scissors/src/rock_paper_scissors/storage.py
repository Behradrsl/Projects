"""Small, transactional SQLite store for finished match summaries."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .game import Match


class StorageError(Exception):
    """History could not be read or saved."""


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connection(self):
        connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if tables:
                    raise StorageError("This database belongs to another application.")
                connection.execute("""CREATE TABLE matches (
                    id TEXT PRIMARY KEY, player TEXT NOT NULL, best_of INTEGER,
                    wins INTEGER NOT NULL, losses INTEGER NOT NULL, draws INTEGER NOT NULL,
                    outcome TEXT NOT NULL, finished_at TEXT NOT NULL
                )""")
                connection.execute("PRAGMA user_version = 1")
            elif version != 1:
                raise StorageError(f"Unsupported history version: {version}.")
            yield connection
            connection.commit()
        except (sqlite3.Error, OSError) as exc:
            raise StorageError(f"Cannot access history: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    def save(self, match_id: str, player: str, match: Match) -> None:
        if not match.finished or match.outcome is None or not match.rounds:
            raise ValueError("Only finished sessions with played rounds can be saved.")
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    match_id,
                    player,
                    match.best_of,
                    match.wins,
                    match.losses,
                    match.draws,
                    match.outcome.value,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self._connection() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM matches ORDER BY finished_at DESC, rowid DESC"
                )
            ]
