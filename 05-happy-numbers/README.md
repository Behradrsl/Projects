# Happy Numbers

A small Python program based on Pytopia's Level I Happy Numbers exercise. Enter a positive whole number and see whether repeatedly adding the squares of its digits reaches 1.

## Run it

Requires **Python 3.10 or newer**. No packages or downloads are needed.

From the repository root:

```bash
cd 05-happy-numbers
python3 main.py
```

On Windows, use `py main.py`. In VS Code, open this project's **`main.py`** and choose **Run Python File in Terminal**.

You can also check a number directly:

```bash
python3 main.py 19
```

Example output:

```text
Checking 19
1² + 9² = 82
8² + 2² = 68
6² + 8² = 100
1² + 0² + 0² = 1
19 is a happy number: the sequence reaches 1.
```

In interactive mode, enter another number to continue, or `q` to quit. `Ctrl+C` also exits. Zero, negative values, decimals, and nonnumeric input are rejected with a clear message.

## How it works

The algorithm follows the teacher's solution: a loop updates the number, while a set remembers numbers already visited. It stops at 1 or the first repeated number. A repeated number means the process has entered a cycle, so the number is not happy.

For example, 2 follows `2 → 4 → 16 → 37 → 58 → 89 → 145 → 42 → 20 → 4`. The second 4 makes the cycle visible.

`happy_numbers.py` exposes two functions:

```python
from happy_numbers import happy_sequence, is_happy

is_happy(19)        # True
is_happy(2)         # False
happy_sequence(19) # [19, 82, 68, 100, 1]
```

Run that example from this project folder so Python can find the module.

## Files

```text
05-happy-numbers/
├── main.py                 # Terminal interaction and printed steps
├── happy_numbers.py        # Sequence and happiness check
├── requirements.txt        # No runtime dependencies
├── requirements-dev.txt
└── tests/test_happy_numbers.py
```

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

Tests cover the course examples, exact sequences, cycle detection, invalid input, and launching from another folder. GitHub Actions runs tests and style checks automatically.

Based on Pytopia's **Lectures → Level I → Happy Numbers** exercise. The terminal prompts, displayed calculation steps, and automated tests extend the teaching solution.
