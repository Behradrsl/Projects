import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from scraper import extract_content, fetch_html, save_reports

ROOT = Path(__file__).resolve().parents[1]


class ScraperTests(unittest.TestCase):
    def test_table_extraction_and_script_removal(self):
        results = extract_content(
            (ROOT / "sample.html").read_text(), ".league-standing"
        )
        self.assertEqual(results[0]["rows"][1], ["Blue FC", "8", "18"])
        self.assertEqual(results[0]["links"][0]["url"], "https://example.com")
        results = extract_content(
            (
                '<div><script>alert(1)</script><a href="javascript:alert(1)">'
                "link</a><p>&lt;script&gt;bad&lt;/script&gt;</p></div>"
            ),
            "div",
        )
        self.assertEqual(results[0]["links"], [])
        with tempfile.TemporaryDirectory() as folder:
            html_path, json_path = save_reports(results, Path(folder))
            html = html_path.read_text()
            self.assertNotIn("<script>", html)
            self.assertNotIn("javascript:", html)
            self.assertEqual(json.loads(json_path.read_text()), results)

    def test_selector_errors_and_relative_links(self):
        with self.assertRaises(ValueError):
            extract_content("<div></div>", ".missing")
        with self.assertRaises(ValueError):
            extract_content("<div></div>", "[")
        results = extract_content(
            '<div><a href="/book">Book</a></div>', "div", "https://example.com/page"
        )
        self.assertEqual(results[0]["links"][0]["url"], "https://example.com/book")
        anchor = extract_content('<a href="/book">Book</a>', "a", "https://example.com")
        self.assertEqual(anchor[0]["links"][0]["url"], "https://example.com/book")

    @patch("scraper.requests.get")
    def test_robots_permissions_and_size_limit(self, get):
        get.return_value = Mock(
            status_code=200, text="User-agent: *\nDisallow: /private"
        )
        with self.assertRaisesRegex(ValueError, "disallows"):
            fetch_html("https://example.com/private")
        self.assertEqual(get.call_count, 1)
        page = MagicMock()
        page.__enter__.return_value = page
        page.status_code = 200
        page.headers = {"Content-Type": "text/html"}
        page.encoding = "utf-8"
        page.iter_content.return_value = [b"<h1>Hello</h1>"]
        get.side_effect = [Mock(status_code=404), page]
        self.assertEqual(fetch_html("https://example.com/page"), "<h1>Hello</h1>")
        page.iter_content.return_value = [b"x" * 2_000_001]
        get.side_effect = [Mock(status_code=404), page]
        with self.assertRaisesRegex(ValueError, "2 MB"):
            fetch_html("https://example.com/page")

    def test_default_cli_creates_reports_from_another_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "--output", folder],
                cwd=folder,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Blue FC", (Path(folder) / "results.html").read_text())


if __name__ == "__main__":
    unittest.main()
