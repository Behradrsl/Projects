# Password Generator

A simple Python command-line tool for generating random passwords, memorable word passwords, and PIN codes. Based on the Password Generator exercise in Pytopia's Level I lectures.

The project follows the course's class-based solution: an abstract `PasswordGenerator` base class and three subclasses, each with its own `generate()` method. A small terminal menu lets you choose a type and adjust its options.

## Getting started

Requires **Python 3.10 or newer**.

From the repository root, on macOS or Linux:

```bash
cd 03-password-generator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m nltk.downloader words
python main.py
```

On Windows PowerShell:

```powershell
cd 03-password-generator
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m nltk.downloader words
python main.py
```

The NLTK word list is a one-time download for memorable passwords. Once it is installed, all three generators work offline. Random passwords and PINs also work without downloading the word list.

After installation, `password-generator` and `python -m password_generator` also start the menu.

## Using the menu

```text
Password Generator
Choose a type. Press Enter at a prompt to use its default.

1. Random password
2. Memorable password
3. PIN code
0. Exit
Your choice:
```

Choose a type, answer the prompts, and the result appears in the terminal. Press Enter to accept a default. Choose `0` or press `Ctrl+C` to exit.

| Type | Options | Default |
| --- | --- | --- |
| Random password | Length (8–128), include numbers, include symbols | 16 characters, numbers and symbols enabled |
| Memorable password | Word count (3–12), separator, capitalize each word | 4 words, hyphens, lowercase |
| PIN code | Length (4–12) | 6 digits |

Random passwords always include lowercase and uppercase letters, plus at least one number and symbol when enabled. Memorable passwords choose words independently, so repeats are possible. The NLTK vocabulary is filtered to alphabetic ASCII words of 4–8 letters; some words may be uncommon. PINs are strings so leading zeroes are preserved.

## Using the classes

```python
from password_generator.generators import (
    MemorablePasswordGenerator,
    PinCodeGenerator,
    RandomPasswordGenerator,
)

print(RandomPasswordGenerator(length=20).generate())
print(MemorablePasswordGenerator(no_of_words=5, capitalization=True).generate())
print(PinCodeGenerator(length=6).generate())
```

For a custom vocabulary, pass `vocabulary=["river", "cloud", "forest", "stone"]` to `MemorablePasswordGenerator`. This also makes it possible to test the class without downloading NLTK data.

## What this project practices

- Abstract classes, inheritance, and method overriding
- String handling and configurable generators
- User input validation and readable terminal interaction
- Automated tests with Python's `unittest`

The main change from the teaching solution is using Python's [`secrets`](https://docs.python.org/3/library/secrets.html) module for password randomness. Generated values are only printed; the application does not save them. They remain visible in terminal scrollback. Short PINs and small custom vocabularies provide fewer possible combinations, and no password-strength score is claimed.

## Project structure

```text
03-password-generator/
├── main.py                         # Run from a checkout
├── pyproject.toml                  # Installation and tool configuration
├── requirements.txt
├── src/password_generator/
│   ├── __init__.py
│   ├── __main__.py                  # Terminal menu and input prompts
│   └── generators.py               # Base class and three generators
└── tests/
    ├── test_generators.py
    └── test_cli.py
```

## Tests

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

Tests use a small supplied vocabulary and do not need the corpus or network access. GitHub Actions runs the tests and style checks automatically.

## Troubleshooting

- **Missing word list:** run `python -m nltk.downloader words` in the same environment. See the [NLTK data instructions](https://www.nltk.org/data.html) for custom download locations.
- **Python certificate error on macOS:** if you installed Python from python.org, run its `Install Certificates.command` from `/Applications/Python 3.x/`, then retry the download. Keep certificate verification enabled.
- **Module not found:** activate the virtual environment and run `python -m pip install -r requirements.txt` from this project folder.

## Course reference

Adapted from the [Pytopia Password Generator exercise](https://github.com/pytopia/Project-Based-Python/tree/59b349e0423d8260ce77e4fc752dd8c111ed3349/Lectures/06%20Level%20I/02%20Password%20Generator), following its object-oriented solution and NLTK vocabulary requirement.
