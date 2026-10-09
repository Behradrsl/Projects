# Number Guesser

**A terminal game built around clear rules, reliable persistence, and a testable Python architecture.**

Guess a randomly selected number, use higher/lower hints to narrow the search, and finish before your attempts run out. Choose a difficulty, track your performance over time, and compare winning rounds on a local leaderboard.

This project extends the course's Number Guesser brief into a complete command-line application. It demonstrates package organization, domain modeling, defensive input validation, file persistence, automated testing, and continuous integration.

## Quick start

Requires **Python 3.10 or newer**. The game has **no third-party runtime dependencies**.

From this project's directory:

```bash
python3 main.py
```

On Windows, use `py main.py` if `python3` is unavailable.

To go straight into a round:

```bash
python3 main.py --name Ada --difficulty normal
```

## Install the command

Create a virtual environment and install the package in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
number-guesser
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

After installation, `python -m number_guesser` is also supported. Installation needs setuptools as a build dependency; direct execution with `main.py` works without downloading anything.

## Gameplay

| Difficulty | Number range | Attempts | Penalty per wrong guess |
| --- | --- | --- | --- |
| Easy | 1–50 | 8 | 10 points |
| Normal | 1–100 | 7 | 15 points |
| Hard | 1–1,000 | 10 | 10 points |

Every round starts at 100 points. A winning score is `max(0, 100 − wrong_guesses × penalty)`. Losing or abandoning a round scores zero. A correct guess on the last attempt still wins.

Each incorrect guess provides a direction and updates the possible range. Invalid input, numbers outside the original range, and repeated guesses cost neither points nor attempts. A distinct guess outside the narrowed hint range is still a valid guess and costs an attempt. The difficulty settings allow enough attempts for a binary-search strategy to succeed.

During a round:

| Input | Action |
| --- | --- |
| A whole number | Submit a guess |
| `help` or `?` | Show the rules and commands |
| `history` | List guesses in the current round |
| `quit`, `q`, or `exit` | Abandon the round and exit |

After a round, replay, change difficulty, view personal statistics, or exit. `Ctrl+C` and end-of-input exit cleanly; when they occur during a round, the round is recorded as abandoned unless saving is disabled.

### Example session

An illustrative normal round with a secret of 42:

```text
Ada, a number between 1 and 100 is waiting.
Normal · 7 attempts · 15 points per wrong guess
Type help for commands.

Possible range: 1–100  |  Attempts left: 7  |  Score: 100
Your guess > 50
Go lower!

Possible range: 1–49  |  Attempts left: 6  |  Score: 85
Your guess > 42

Correct! The number was 42.
You won in 2 guesses · Final score: 85/100
```

## Command-line options

```bash
# View all saved statistics and top five winning rounds per difficulty
python3 main.py --stats

# Filter statistics by an exact player name
python3 main.py --stats --name Ada

# Practice without writing a history file
python3 main.py --difficulty hard --no-save

# Use a different history location
python3 main.py --scores-file ./data/scores.json

# Inspect available arguments or the package version
python3 main.py --help
python3 main.py --version
```

Player names are case-sensitive, contain 1–24 printable characters, and default to `Player`. Rankings compare rounds within the same difficulty: highest score first, then fewer guesses, then earliest timestamp. Statistics include abandoned rounds in the win-rate denominator.

## Design

```text
01-number-guesser-game/
├── main.py                     # Checkout entry point
├── pyproject.toml              # Package metadata and console command
├── src/
│   └── number_guesser/
│       ├── __init__.py
│       ├── __main__.py          # python -m number_guesser
│       ├── game.py              # Round state, validation, hints, scoring
│       ├── cli.py               # Terminal interaction and orchestration
│       └── storage.py           # Validated JSON records and atomic writes
└── tests/
    ├── test_game.py
    ├── test_cli.py
    └── test_storage.py
```

The game engine has no terminal or filesystem dependencies. It owns the round state and permits transitions from `playing` to `won`, `lost`, or `quit`. Finished rounds reject further guesses. Supplying a secret in tests makes results deterministic without adding a cheat option to the CLI.

The CLI handles prompts and translates user actions into engine calls. Immutable dataclasses represent difficulty profiles, guess results, and saved rounds. The storage module validates the versioned JSON schema and the consistency of scores before accepting historical data.

JSON keeps the history easy to inspect and avoids a database dependency for a local game. Saved data lives at `~/.number_guesser/scores.json`, independent of the working directory. Timestamps use UTC. Writes go to a temporary file in the same directory, are flushed to disk, and replace the destination atomically. A malformed or unsupported history file is preserved, a warning explains the failure, and gameplay continues without saving that round.

This is a local, single-process application. Simultaneous processes writing to the same history file are unsupported. Scores are editable local data, so the leaderboard is intended for personal tracking rather than competitive verification. To recover from corrupt history, back up the file and choose a new path with `--scores-file`.

## Development and verification

After installing the package, run the standard-library test suite:

```bash
python -m unittest discover -s tests -v
```

On macOS or Linux, tests also run directly from a checkout:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The suite covers scoring and boundaries, last-attempt wins, invalid and repeated guesses, replay, menu navigation, terminal interruptions, persistence, malformed records, and preservation of existing data when an atomic replacement fails.

Lint and formatting checks use Ruff:

```bash
python -m pip install ruff==0.11.13
ruff check .
ruff format --check .
```

From the projects repository root, enter `01-number-guesser-game/` before running the commands above. The project's GitHub Actions workflow lives at `.github/workflows/number-guesser.yml` in the repository root. It runs tests on Python 3.10–3.13 and checks lint and formatting when this project changes.
