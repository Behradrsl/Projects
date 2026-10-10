# Number to Words

A terminal tool that converts whole numbers into readable English, including zero and negative numbers.

## Run it

Requires **Python 3.10 or newer**.

```bash
cd 12-number-to-words
python3 main.py
```

No packages are needed. On Windows, use `py main.py`.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. Use `Ctrl+C` to exit.

## Use it

Enter a number at the prompt, or pass it directly:

```bash
python3 main.py 12345
python3 main.py -42
```

```text
twelve thousand three hundred forty-five
minus forty-two
```

The supported range is **−999,999,999,999 to 999,999,999,999**. Enter digits without commas or decimal points. Interactive mode keeps accepting numbers until you type `q`; invalid input lets you try again.

## How it works

`number_words.py` maps values below 20 to words, joins tens with hyphens, and recursively separates hundreds, thousands, millions, and billions. It uses American-style wording without “and”: `101` becomes `one hundred one`.

`main.py` handles terminal input and command-line arguments. Tests cover scale boundaries, negative values, invalid types, and running from another folder.

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and style checks on Python 3.10 and 3.13.
