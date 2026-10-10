"""A two-player game with numbered cells and validated moves."""

import random

WINNING_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


class TicTacToe:
    def __init__(self, first_player=None):
        if first_player is not None and first_player not in ("X", "O"):
            raise ValueError("The first player must be X or O.")
        self.board = [""] * 9
        self.current_player = first_player or random.choice(("X", "O"))

    @property
    def winner(self):
        for a, b, c in WINNING_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        return None

    @property
    def finished(self):
        return self.winner is not None or all(self.board)

    def play(self, cell: int):
        if self.finished:
            raise ValueError("This game is finished. Start a new round.")
        if isinstance(cell, bool) or not isinstance(cell, int) or not 1 <= cell <= 9:
            raise ValueError("Choose a cell number from 1 to 9.")
        if self.board[cell - 1]:
            raise ValueError("That cell is taken. Choose an empty cell.")
        self.board[cell - 1] = self.current_player
        if not self.finished:
            self.current_player = "O" if self.current_player == "X" else "X"

    def __str__(self):
        cells = [mark or str(index + 1) for index, mark in enumerate(self.board)]
        rows = [" " + " | ".join(cells[i : i + 3]) + " " for i in (0, 3, 6)]
        return "\n---+---+---\n".join(rows)
