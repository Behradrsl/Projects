# Contact Book

A terminal app for adding, finding, editing, and deleting contacts. Names, phone numbers, emails, and addresses are saved in a local SQLite database, so they are still there when you reopen the app.

## Run it

Python 3.10 or newer. No packages are needed.

```bash
cd 07-contact-book
python3 main.py
```

In VS Code, open **main.py** and choose **Run Python File in Terminal**. On Windows, use `py main.py`.

```text
Contact Book
1. Add contact
2. View contacts
3. Search contacts
4. Edit contact
5. Delete contact
0. Exit
```

Choose an option and follow the prompts. Only the name is required. Phone numbers are kept as text, preserving `+` signs and leading zeroes. Email validation checks basic formatting; it does not verify that an address exists.

For example, add `Ana`, `+49 123`, `ana@example.com`, and `Berlin`. Search for `ana` or `berlin` to find the contact. Each result shows an ID, which you use when editing or deleting. Two people can share a name and still have different IDs.

When editing, **Enter** keeps the existing value; **-** clears an optional field. Deleting asks for confirmation and defaults to keeping the contact. Enter `0` at the menu to exit; `Ctrl+C` also exits.

## How it works

`contact_book.py` contains the `ContactBook` class and database operations. `main.py` handles the menu and prompts. SQLite assigns each contact a unique ID, and parameterized queries safely handle names such as `O'Connor`. A search matches any part of a name, phone, email, or address without changing the stored data.

The default database is `data/contacts.db` inside this project, regardless of the folder you launch from. That folder is excluded from Git. Copy the database file while the app is closed if you want a backup.

To use a different database:

```bash
python3 main.py --database /path/to/contacts.db
```

## Checks

```bash
python3 -m unittest discover -s tests -v
```

Tests cover saving and reopening contacts, edits and deletions, duplicate names, search, invalid input, and terminal use from another folder.

Optional style checks:

```bash
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
```
