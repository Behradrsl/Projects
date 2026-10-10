"""Store and manage contacts in a local SQLite database."""

import sqlite3
from pathlib import Path


class ContactBook:
    def __init__(self, database: str | Path):
        database = Path(database).expanduser()
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.execute(
                """CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    address TEXT NOT NULL DEFAULT ''
                )"""
            )

    @staticmethod
    def validate(name: str, phone: str, email: str, address: str) -> tuple[str, ...]:
        fields = tuple(value.strip() for value in (name, phone, email, address))
        name, phone, email, address = fields
        if not name:
            raise ValueError("A contact needs a name.")
        if any(len(value) > 500 for value in fields):
            raise ValueError("Keep each field within 500 characters.")
        if email and (email.count("@") != 1 or any(c.isspace() for c in email)):
            raise ValueError(
                "Enter an email with one @ and no spaces, or leave it blank."
            )
        if email and not all(email.split("@")):
            raise ValueError("Enter both parts of the email address.")
        return fields

    def add_contact(self, name: str, phone="", email="", address="") -> int:
        fields = self.validate(name, phone, email, address)
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO contacts (name, phone, email, address) "
                "VALUES (?, ?, ?, ?)",
                fields,
            )
        return cursor.lastrowid

    def get_contact(self, contact_id: int) -> dict:
        row = self.connection.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        if row is None:
            raise ValueError("No contact has that ID.")
        return dict(row)

    def list_contacts(self, search: str = "") -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM contacts ORDER BY name COLLATE NOCASE, id"
        ).fetchall()
        query = search.strip().casefold()
        return [
            dict(row)
            for row in rows
            if not query
            or any(
                query in str(row[key]).casefold()
                for key in ("name", "phone", "email", "address")
            )
        ]

    def update_contact(
        self, contact_id: int, name: str, phone="", email="", address=""
    ):
        fields = self.validate(name, phone, email, address)
        self.get_contact(contact_id)
        with self.connection:
            self.connection.execute(
                "UPDATE contacts SET name=?, phone=?, email=?, address=? WHERE id=?",
                (*fields, contact_id),
            )

    def delete_contact(self, contact_id: int):
        self.get_contact(contact_id)
        with self.connection:
            self.connection.execute("DELETE FROM contacts WHERE id=?", (contact_id,))

    def close(self):
        self.connection.close()
