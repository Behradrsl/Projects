"""Run the contact book menu."""

import argparse
import sqlite3
from pathlib import Path

from contact_book import ContactBook


def show_contacts(contacts):
    if not contacts:
        print("No contacts found. Choose Add contact to create one.")
    for contact in contacts:
        print(f"\n#{contact['id']}  {contact['name']}")
        for field in ("phone", "email", "address"):
            print(f"  {field.title()}: {contact[field] or '—'}")


def read_fields(current=None):
    values = []
    for field in ("name", "phone", "email", "address"):
        if current is None:
            values.append(input(f"{field.title()}: "))
        else:
            value = input(f"{field.title()} [{current[field] or 'empty'}]: ").strip()
            if not value:
                value = current[field]
            elif value == "-":
                value = ""
            values.append(value)
    return values


def run_menu(book):
    while True:
        print("\nContact Book\n1. Add contact\n2. View contacts\n3. Search contacts")
        print("4. Edit contact\n5. Delete contact\n0. Exit")
        choice = input("Your choice: ").strip()
        try:
            if choice == "0":
                return
            if choice == "1":
                contact_id = book.add_contact(*read_fields())
                print(f"Contact saved with ID {contact_id}.")
            elif choice == "2":
                show_contacts(book.list_contacts())
            elif choice == "3":
                show_contacts(book.list_contacts(input("Search: ")))
            elif choice in ("4", "5"):
                contact_id = int(input("Contact ID (shown beside the name): "))
                contact = book.get_contact(contact_id)
                if choice == "4":
                    print("Enter keeps a value. Type - to clear an optional field.")
                    book.update_contact(contact_id, *read_fields(contact))
                    print("Contact updated.")
                elif input(f"Delete {contact['name']}? [y/N]: ").strip().lower() == "y":
                    book.delete_contact(contact_id)
                    print("Contact deleted.")
                else:
                    print("Deletion cancelled.")
            else:
                print("Choose an option from 0 to 5.")
        except ValueError as error:
            print(f"Could not save or find the contact: {error}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Manage contacts stored on your computer."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).resolve().parent / "data/contacts.db",
    )
    args = parser.parse_args(argv)
    book = None
    try:
        book = ContactBook(args.database)
        print(f"Contacts are saved in {args.database.expanduser().resolve()}")
        run_menu(book)
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        return 0
    except (OSError, sqlite3.Error) as error:
        print(f"Cannot use the contact database: {error}")
        return 1
    finally:
        if book is not None:
            book.close()


if __name__ == "__main__":
    raise SystemExit(main())
