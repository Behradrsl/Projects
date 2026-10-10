import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

from checker import check_site, check_sites, normalize_url


class CheckerTests(unittest.TestCase):
    def test_normalization_preserves_host_path_and_query(self):
        self.assertEqual(
            normalize_url("example.com/path?q=1#part"), "https://example.com/path?q=1"
        )
        self.assertEqual(
            normalize_url("http://localhost:8080"), "http://localhost:8080/"
        )
        for value in (
            "",
            "ftp://example.com",
            "https://user:secret@example.com",
            "https://bad host",
            "https://example.com:wrong",
        ):
            with self.assertRaises(ValueError):
                normalize_url(value)

    def test_real_http_response_redirect_and_error(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/")
                else:
                    self.send_response(404 if self.path == "/missing" else 200)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            root = f"http://127.0.0.1:{server.server_port}"
            results = check_sites([root, root + "/redirect", root + "/missing", root])
            self.assertEqual(len(results), 3)
            self.assertEqual(
                [r.status for r in results], ["Reachable", "Reachable", "HTTP error"]
            )
            self.assertEqual(results[2].code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    @patch("checker.requests.get")
    def test_timeout_and_connection_error(self, get):
        get.side_effect = requests.Timeout()
        self.assertEqual(check_site("example.com").status, "Timed out")
        get.side_effect = requests.ConnectionError()
        self.assertEqual(check_site("example.com").status, "Connection error")
        for urls in ([], ["example.com"] * 21):
            with self.assertRaises(ValueError):
                check_sites(urls)

    def test_form_results_and_invalid_url(self):
        from checker import SiteResult

        result = SiteResult(
            "https://example.com/", "Reachable", 200, 12.0, "https://example.com/"
        )
        with patch("checker.check_sites", return_value=[result]):
            app = AppTest.from_file(
                str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15
            ).run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.dataframe), 1)
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15
        ).run()
        app.text_area[0].set_value("file:///tmp/private")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
