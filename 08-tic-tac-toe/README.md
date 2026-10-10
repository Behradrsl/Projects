# Tic Tac Toe

A two-player terminal game. Share a keyboard, choose numbered cells, and try to place three matching marks in a row, column, or diagonal.

## Run it

Python 3.10 or newer. No packages are needed.

```bash
cd 08-tic-tac-toe
python3 main.py
```

In VS Code, open **main.py** and choose **Run Python File in Terminal**. On Windows, use `py main.py`.

The starting player is chosen randomly each round. To choose who starts:

```bash
python3 main.py --first X
```

## Play

```text
 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9
```

At your prompt, enter an empty cell number from `1` to `9`. The game replaces it with your mark. Invalid input and occupied cells leave the turn unchanged.

For example, with X starting, moves `1, 4, 2, 5, 3` give X the top row and the win. A full board without a winner is a draw. After the result, type `y` to play again or press Enter to exit. Type `q` during a turn to quit; `Ctrl+C` also exits.

## How it works

`tic_tac_toe.py` contains a small `TicTacToe` class. It stores nine cells, tracks the current player, and checks all eight winning lines after each move. The game ends immediately on a win or after the ninth move without a winner. `main.py` handles input, board display, and replay.

The game is local multiplayer; both players use the same terminal. No account, network connection, or saved data is needed.

## Checks

```bash
python3 -m unittest discover -s tests -v
```

Tests cover every winning line for both starting players, draws, invalid moves, game completion, replay, and launching from another folder.

Optional style checks:

```bash
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
```
