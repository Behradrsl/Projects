# Wordle

A terminal word game: guess a five-letter word in six tries, with optional hints and unlimited rounds.

## Run it

Requires **Python 3.10 or newer**.

```bash
cd 16-wordle
python3 main.py
```

No packages are needed. On Windows, use `py main.py`.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. Use `Ctrl+C` to exit.

## Play

```text
[Letter] = correct position
(Letter) = in the answer, in another position
 Letter  = not used by the answer at that position
```

Enter a word from the bundled `words.txt`. The app ignores capitalization. Invalid or repeated guesses do not use an attempt. Type `?` to see the number of possible answers and up to twelve suggestions, or `q` to quit. At the end of a round, enter `y` to play again.

For example, guessing `allee` against `apple` marks the first A and final E as correct, the first L as misplaced, and the second L and first E as absent. A repeated letter receives credit only when the answer contains another available occurrence.

Optional arguments:

```bash
python3 main.py --seed 42
python3 main.py --words /path/to/words.txt
```

A custom vocabulary needs one five-letter ASCII word per line. `--seed` makes the sequence of answers repeatable for the same vocabulary.

## How it works

`wordle.py` first reserves exact matches, then counts the remaining answer letters to mark misplaced matches correctly. Candidate hints keep only words that would produce the same feedback for every previous guess. `main.py` handles rounds, hints, and terminal display.

The bundled vocabulary is a curated list of common words, not a complete dictionary. Tests cover duplicate letters, win/loss limits, invalid guesses, candidate filtering, and terminal use.

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and style checks on Python 3.10 and 3.13.
