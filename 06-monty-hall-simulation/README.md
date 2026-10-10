# Monty Hall Simulation

A simple terminal game and simulation based on Pytopia's Level I Monty Hall exercise. Play a round yourself, then compare how often keeping or switching doors wins.

## Run it

Requires **Python 3.10 or newer**. No packages or downloads are needed.

From the repository root:

```bash
cd 06-monty-hall-simulation
python3 main.py
```

On Windows, use `py main.py`. In VS Code, open this project's **`main.py`** and choose **Run Python File in Terminal**.

```text
1. Play a round
2. Compare strategies
0. Exit
Your choice:
```

- **Play a round:** choose door 1, 2, or 3. Monty opens an unchosen door with a goat. Enter `k` to keep your door or `s` to switch, then see the prize.
- **Compare strategies:** choose 1–1,000,000 games. Press Enter for 10,000. The program prints the wins and win percentage for each strategy.
- Choose `0` or press `Ctrl+C` to exit.

For a repeatable simulation without the menu:

```bash
python3 main.py --games 10000 --seed 42
```

`--seed` is optional. Reusing the same seed reproduces the result in the same Python environment. `python3 main.py --help` shows the command-line options.

## Why switching helps

Your first choice has a 1-in-3 chance of being the car. The two other doors together have a 2-in-3 chance. Monty knows where the car is and removes a goat door, leaving the other unopened door to carry that 2-in-3 chance.

The simulation uses the standard rules: Monty always reveals an unchosen goat door and always offers a switch. If your first choice is the car, he randomly chooses either goat door. Changing these assumptions changes the problem.

Over many games, keeping tends toward **33.3%** wins and switching toward **66.7%**. Small samples can differ considerably.

Both strategies are evaluated on the **same simulated games**, rather than separate runs. For every game, exactly one strategy wins, so their win counts sum to the number of games. Python's `random.Random` is appropriate here for a simulation; the optional seed makes it repeatable.

## Files

```text
06-monty-hall-simulation/
├── main.py                 # Play, menu, and simulation output
├── monty_hall.py           # Door rules and simulation functions
├── requirements.txt        # No runtime dependencies
├── requirements-dev.txt
└── tests/test_monty_hall.py
```

The logic stays separate from terminal prompts. `create_round()` records the prize and door choices, `monty_hall_game()` simulates one strategy, and `simulate_games()` returns the keep/switch win counts.

## Checks

Run the tests without installing anything:

```bash
python3 -m unittest discover -s tests -v
```

Optional style checks:

```bash
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
```

Tests check all nine prize/initial-choice combinations, both possible host reveals when the contestant picks the car, seed repeatability, invalid input, terminal play, and launching from another folder. They establish the 3-versus-6 advantage exactly, without relying on a random sample to pass.

GitHub Actions runs the checks automatically.

Based on Pytopia's **Lectures → Level I → Monty Hall Problem Simulation** exercise. This version keeps the terminal focus, adding repeatable comparisons and tests; the optional Streamlit extension is not included.
