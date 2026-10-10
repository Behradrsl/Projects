import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from name_stats import load_records, summarize_name

ROOT = Path(__file__).resolve().parents[1]


class StatisticsTests(unittest.TestCase):
    def test_counts_aggregate_case_and_duplicates(self):
        rows = load_records(
            b"name,region,count\nAlex,North,3\nalex,North,1\nAlex,South,4\n"
        )
        self.assertEqual(
            summarize_name(rows, "ALEX"),
            [
                {"region": "North", "count": 4, "share_percent": 50.0},
                {"region": "South", "count": 4, "share_percent": 50.0},
            ],
        )
        self.assertEqual(summarize_name(rows, "unknown"), [])

    def test_unicode_names_and_bom(self):
        rows = load_records("﻿name,region,count\nÉva,North,2\n".encode("utf-8"))
        self.assertEqual(summarize_name(rows, "E\u0301VA")[0]["count"], 2)

    def test_invalid_data(self):
        for data in (
            b"name,count\nAlex,1",
            b"name,region,count\nAlex,N,-1",
            b"name,region,count\nAlex,N,1.5",
            b"name,region,count\nAlex,N,0",
            b"\xff",
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                load_records(data)

    def test_sample_app_and_name_change(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        self.assertIn("200 recorded occurrences of Alex", app.subheader[0].value)
        app.selectbox[0].set_value("Maria").run()
        self.assertFalse(app.exception)
        self.assertIn("260 recorded occurrences of Maria", app.subheader[0].value)


if __name__ == "__main__":
    unittest.main()
