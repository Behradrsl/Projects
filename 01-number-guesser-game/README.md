# Number Guesser

A terminal game with higher and lower hints, three difficulty levels, and saved scores. Enter a guess, narrow the possible range, and find the number before your attempts run out.

## Run it

Requires **Python 3.10 or newer**. No packages are needed.

From the repository root:

```bash
cd 01-number-guesser-game
python3 main.py
```

On Windows, use `py main.py`. In VS Code, open **main.py** and choose **Run Python File in Terminal**.

Enter a player name and choose a difficulty. Press Enter to use the default name (`Player`) or difficulty (`normal`). To skip those prompts:

```bash
python3 main.py --name Ada --difficulty normal
```

## How to play

| Difficulty | Range | Attempts | Points lost per wrong guess |
| --- | --- | --- | --- |
| Easy | 1–50 | 8 | 10 |
| Normal | 1–100 | 7 | 15 |
| Hard | 1–1,000 | 10 | 10 |

Each wrong guess gives a higher or lower hint. The terminal shows the remaining range and attempts before your next guess. Invalid input, repeated guesses, and numbers outside the original range do not use an attempt. A new guess outside the narrowed range still uses an attempt.

A win starts at 100 points, minus the penalty for each wrong guess, with a minimum of zero. Losing or quitting a round scores zero. A correct guess on the last attempt still wins.

For example, in a normal round where the secret number is 42:

```text
Ada, guess a number between 1 and 100.
Normal difficulty. 7 attempts.
Type help for rules, history for guesses, or quit to exit.

Range: 1–100 | Attempts left: 7
Your guess: 50
Go lower!

Range: 1–49 | Attempts left: 6
Your guess: 42

Correct! The number was 42.
You won in 2 guesses. Final score: 85/100
```

During a round, type `help` for rules, `history` to see your guesses, or `quit` to exit. After the result, press Enter to play again, type `m` to change difficulty, `s` to see statistics, or `n` to exit. `Ctrl+C` and end-of-input also exit cleanly.

## Saved results

Rounds are saved to `~/.number_guesser/scores.json`. Statistics include wins, losses, abandoned rounds, win rate, and the top five winning rounds for each difficulty. Rankings use score, then fewest guesses, then earliest date. Player names are case-sensitive and accept 1–24 printable characters.

```bash
# Show all saved results
python3 main.py --stats

# Show one player's results
python3 main.py --stats --name Ada

# Play without saving
python3 main.py --no-save

# Choose a different history file
python3 main.py --scores-file ./data/scores.json

# Show all options
python3 main.py --help
```

If the history file cannot be read or written, the game reports the problem and continues. Existing unreadable data is preserved. Use a different `--scores-file` path to start a new history. The history file is intended for one running game at a time.

## How the code works

- `main.py` launches the game directly from a checkout.
- `src/number_guesser/cli.py` handles prompts, menus, and replay.
- `src/number_guesser/game.py` validates guesses and manages hints, attempts, and scoring.
- `src/number_guesser/storage.py` reads and validates JSON records and saves them with atomic file replacement.

The game logic is independent of the terminal and storage, so it can be tested with a fixed secret number.

## Optional installation

To install the `number-guesser` command, create and activate a virtual environment, then run:

```bash
python3 -m pip install -e .
number-guesser
```

After installation, `python3 -m number_guesser` also works.

## Checks

From this project folder, run the standard-library tests without installing the package:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

After the optional installation, the cross-platform command is:

```bash
python3 -m unittest discover -s tests -v
```

Tests cover scoring, range boundaries, invalid and repeated guesses, replay, interruptions, statistics, and saving results. Optional style checks:

```bash
python3 -m pip install ruff==0.11.13
ruff check .
ruff format --check .
```
