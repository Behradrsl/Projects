"""Versioned, validated JSON storage with atomic replacement.

Malformed history is preserved: it is never silently reset or overwritten.
This local store is intended for a single game process at a time.
"""

import json
import os
import tempfile
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .game import DIFFICULTIES, Game, Status


class StorageError(Exception):
    """A history file could not be read, validated, or written."""


@dataclass(frozen=True)
class Record:
    player: str
    difficulty: str
    outcome: str
    attempts: int
    score: int
    played_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.player, str) or not 1 <= len(self.player) <= 24:
            raise ValueError("Invalid player name.")
        if not self.player.strip() or any(not c.isprintable() for c in self.player):
            raise ValueError("Invalid player name.")
        if not isinstance(self.difficulty, str) or self.difficulty not in DIFFICULTIES:
            raise ValueError("Unknown difficulty.")
        if self.outcome not in ("won", "lost", "quit"):
            raise ValueError("Invalid outcome.")
        mode = DIFFICULTIES[self.difficulty]
        if type(self.attempts) is not int or not 0 <= self.attempts <= mode.attempts:
            raise ValueError("Invalid attempt count.")
        if type(self.score) is not int or not 0 <= self.score <= 100:
            raise ValueError("Invalid score.")
        if self.outcome == "won":
            if self.attempts < 1 or self.score != max(0, 100 - (self.attempts - 1) * mode.penalty):
                raise ValueError("Score does not match the winning round.")
        elif self.score != 0 or (self.outcome == "lost" and self.attempts != mode.attempts):
            raise ValueError("Score or attempt count does not match the outcome.")
        if not isinstance(self.played_at, str):
            raise ValueError("Invalid timestamp.")
        if datetime.fromisoformat(self.played_at).tzinfo is None:
            raise ValueError("Timestamp must include a timezone.")

    @classmethod
    def from_game(cls, player: str, game: Game) -> "Record":
        if game.status == Status.PLAYING:
            raise ValueError("Only finished rounds can be saved.")
        return cls(
            player,
            game.difficulty.name,
            game.status.value,
            len(game.guesses),
            game.score,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )


class ScoreStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[Record]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or type(raw.get("version")) is not int:
                raise ValueError("Invalid history format.")
            if raw["version"] != 1 or not isinstance(raw.get("rounds"), list):
                raise ValueError("Unsupported history format.")
            return [Record(**item) for item in raw["rounds"]]
        except FileNotFoundError:
            return []
        except (OSError, ValueError, TypeError) as exc:
            raise StorageError(f"Cannot read history at {self.path}: {exc}") from exc

    def append(self, record: Record) -> None:
        rounds = self.load()
        rounds.append(record)
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=".scores-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump({"version": 1, "rounds": [asdict(r) for r in rounds]}, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise StorageError(f"Cannot save history at {self.path}: {exc}") from exc
        finally:
            if temporary is not None:
                # A cleanup failure must not mask a more useful storage error.
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)
