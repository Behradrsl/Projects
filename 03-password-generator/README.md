# Password Generator

A small Python project based on the teacher's class-based Password Generator solution. Choose a random password, a memorable word password, or a numeric PIN from a terminal menu.

## Run it

Requires **Python 3.10 or newer**. The app works without installing packages or downloading data.

From the repository root:

```bash
cd 03-password-generator
python3 main.py
```

On Windows, use `py main.py`.

In VS Code, open **`03-password-generator/main.py`** and choose **Run Python File in Terminal**. The menu needs a terminal that accepts input. `__init__.py` is a package file, not the application launcher.

## How to use it

```text
Password Generator
Choose a type. Press Enter at a prompt to use its default.

1. Random password
2. Memorable password
3. PIN code
0. Exit
Your choice:
```

Choose `1`, `2`, or `3`, then answer the prompts. Press Enter to use a default.

| Type | Options | Default |
| --- | --- | --- |
| Random password | Length (8–128), numbers, symbols | 16 characters, numbers and symbols included |
| Memorable password | Words (3–12), separator, capitalization | 4 words separated by hyphens |
| PIN code | Length (4–12) | 6 digits |

After a result appears:

- Press **Enter** to generate another with the same settings.
- Type **m** to return to the menu.
- Type **q** to quit. `Ctrl+C` also exits cleanly.

For memorable passwords, type `none` at the separator prompt to join words without separators, or enter a space to separate them with spaces.

Random passwords include uppercase and lowercase letters and every enabled character type. Word passwords use familiar words, with repeats allowed. PINs preserve leading zeroes. Nothing is saved by the app; results remain visible in your terminal scrollback.

## How the code works

`PasswordGenerator` is an abstract base class. `RandomPasswordGenerator`, `MemorablePasswordGenerator`, and `PinCodeGenerator` each implement `generate()`, following the course's object-oriented design. Python's [`secrets`](https://docs.python.org/3/library/secrets.html) module supplies the randomness.

```text
03-password-generator/
├── main.py                     # Start here
├── README.md
├── pyproject.toml
├── requirements.txt
├── src/password_generator/
│   ├── __init__.py
│   ├── __main__.py              # Menu and input prompts
│   ├── generators.py           # Base class and three generators
│   └── words.txt               # Bundled common-word fallback
└── tests/
    ├── test_generators.py
    └── test_cli.py
```

The bundled word list keeps the project runnable offline. To use the course's NLTK corpus, optionally install it:

```bash
python3 -m pip install -e ".[corpus]"
python3 -m nltk.downloader words
```

When NLTK and its corpus are available, memorable passwords use its `en-basic` list of familiar English words. Otherwise, they use `words.txt`. Neither small word list is a replacement for a large password-manager passphrase dictionary.

## Optional installation

To install the `password-generator` command or import the classes into another project:

```bash
python3 -m pip install -r requirements.txt
```

For example:

```python
from password_generator.generators import RandomPasswordGenerator

print(RandomPasswordGenerator(length=20).generate())
```

## Tests

The tests cover character options, lengths, leading zeroes, word-list fallbacks, input validation, regeneration, and running the app without installed dependencies.

```bash
python3 -m pip install -e ".[dev]"
python3 -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

## Course reference

Based on Pytopia's Level I Password Generator exercise and its class-based solution. The terminal menu, bundled fallback, validation, and automated tests are additions to make the exercise easier to run and explore.
