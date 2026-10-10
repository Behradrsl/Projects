import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from contact_book import ContactBook

ROOT = Path(__file__).resolve().parents[1]


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "contacts.db"
        self.book = ContactBook(self.path)

    def tearDown(self):
        self.book.close()
        self.temp.cleanup()

    def test_crud_and_reopen(self):
        identifier = self.book.add_contact(
            " Ana ", "+49 123", "ana@example.com", "Berlin"
        )
        self.assertEqual(self.book.get_contact(identifier)["name"], "Ana")
        self.book.update_contact(identifier, "Ana Smith", "", "ana@example.com", "")
        self.book.close()
        self.book = ContactBook(self.path)
        contact = self.book.get_contact(identifier)
        self.assertEqual(contact["name"], "Ana Smith")
        self.assertEqual(contact["phone"], "")
        self.book.delete_contact(identifier)
        self.assertEqual(self.book.list_contacts(), [])
        with self.assertRaises(ValueError):
            self.book.get_contact(identifier)

    def test_duplicate_names_have_different_ids(self):
        first = self.book.add_contact("Alex", "111")
        second = self.book.add_contact("Alex", "222")
        self.book.delete_contact(first)
        self.assertEqual(self.book.get_contact(second)["phone"], "222")

    def test_search_literal_quotes_and_unicode(self):
        self.book.add_contact("O'Connor", "123", "oc@example.com", "München")
        self.book.add_contact("Zoe")
        self.assertEqual(len(self.book.list_contacts("MÜNCHEN")), 1)
        self.assertEqual(len(self.book.list_contacts("O'Connor")), 1)
        self.assertEqual(self.book.list_contacts("' OR 1=1 --"), [])
        self.assertEqual(self.book.list_contacts("%"), [])

    def test_validation_leaves_existing_data_unchanged(self):
        identifier = self.book.add_contact("Ana")
        for name, email in [
            ("", ""),
            ("Ana", "invalid"),
            ("Ana", "@example.com"),
            ("Ana", "a@"),
            ("Ana", "a @b"),
        ]:
            with self.subTest(name=name, email=email), self.assertRaises(ValueError):
                self.book.update_contact(identifier, name, email=email)
        self.assertEqual(self.book.get_contact(identifier)["email"], "")
        with self.assertRaises(ValueError):
            self.book.delete_contact(999)

    def test_terminal_add_search_cancel_delete_from_another_folder(self):
        answers = "1\nAna\n123\nana@example.com\nBerlin\n3\nANA\n5\n1\nn\n2\n0\n"
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), "--database", str(self.path)],
            input=answers,
            text=True,
            capture_output=True,
            cwd=self.temp.name,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Contact saved with ID 1", result.stdout)
        self.assertIn("Deletion cancelled", result.stdout)
        self.assertEqual(len(self.book.list_contacts()), 1)

    def test_invalid_input_and_eof_exit(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), "--database", str(self.path)],
            input="4\nwrong\n",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
