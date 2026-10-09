import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rock_paper_scissors.game import Move
from rock_paper_scissors.storage import StorageError
from rock_paper_scissors.web import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app(Path(self.directory.name) / "history.sqlite3")
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.csrf = self.client.get("/api/state").json["csrf"]
        self.random = patch("rock_paper_scissors.web.secrets.choice", return_value=Move.SCISSORS)
        self.random.start()
        self.addCleanup(self.random.stop)

    def post(self, path, data):
        return self.client.post(path, json=data, headers={"X-CSRF-Token": self.csrf})

    def start(self, best_of=3, player="Ada"):
        response = self.post("/api/matches", {"best_of": best_of, "player": player})
        self.assertEqual(response.status_code, 200)
        return response.json["match"]

    def turn(self, match, move="rock"):
        return self.post(
            "/api/play", {"move": move, "match_id": match["id"], "revision": match["revision"]}
        )

    def test_index_assets_and_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your move", response.data)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        for path in ("/static/styles.css", "/static/app.js", "/static/favicon.svg"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_full_match_saved_once_and_scores_cannot_be_forged(self):
        match = self.start()
        self.assertNotIn("next_move", match)
        response = self.post(
            "/api/play",
            {
                "move": "rock",
                "match_id": match["id"],
                "revision": 0,
                "wins": 100,
                "computer": "paper",
            },
        )
        match = response.json["match"]
        self.assertEqual(match["wins"], 1)
        self.assertEqual(match["rounds"][0]["computer"], "scissors")
        match = self.turn(match).json["match"]
        self.assertEqual((match["finished"], match["outcome"]), (True, "win"))
        self.assertEqual(self.turn(match).status_code, 400)
        history = self.client.get("/api/history").json
        self.assertEqual(len(history["records"]), 1)
        self.assertEqual(history["stats"]["win_rate"], 100)

    def test_duplicate_request_is_rejected_with_current_state(self):
        match = self.start()
        self.assertEqual(self.turn(match).status_code, 200)
        response = self.turn(match)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["match"]["wins"], 1)

    def test_old_match_cannot_submit_to_new_match(self):
        old = self.start()
        self.start()
        self.assertEqual(self.turn(old).status_code, 409)

    def test_invalid_inputs_do_not_consume_rounds(self):
        match = self.start()
        for value in ("lizard", None, [], True):
            with self.subTest(value=value):
                self.assertEqual(self.turn(match, value).status_code, 400)
        state = self.client.get("/api/state").json["match"]
        self.assertEqual(state["rounds"], [])
        self.assertEqual(state["revision"], 0)

    def test_invalid_names_and_formats_return_useful_errors(self):
        for name in ("", "x" * 25, "\x1b[31m", [], None):
            self.assertEqual(self.post("/api/matches", {"player": name}).status_code, 400)
        for mode in (True, "3", 2, []):
            self.assertEqual(self.post("/api/matches", {"best_of": mode}).status_code, 400)

    def test_missing_csrf_and_non_json_requests_are_rejected(self):
        self.assertEqual(self.client.post("/api/matches", json={}).status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/matches", data="hi", headers={"X-CSRF-Token": self.csrf}
            ).status_code,
            415,
        )
        self.assertEqual(self.post("/api/matches", []).status_code, 400)

    def test_browser_sessions_are_isolated_and_refresh_restores_match(self):
        match = self.start()
        self.turn(match)
        self.assertEqual(self.client.get("/api/state").json["match"]["wins"], 1)
        other = self.app.test_client()
        self.assertIsNone(other.get("/api/state").json["match"])

    def test_replacing_active_match_saves_it_as_abandoned(self):
        match = self.start()
        self.turn(match)
        self.start(5)
        record = self.client.get("/api/history").json["records"][0]
        self.assertEqual(record["outcome"], "abandoned")

    def test_free_play_saves_current_score_and_is_excluded_from_match_rate(self):
        match = self.start(None)
        match = self.turn(match).json["match"]
        response = self.post("/api/finish", {"match_id": match["id"], "revision": 1})
        self.assertEqual(response.json["match"]["outcome"], "win")
        history = self.client.get("/api/history").json
        self.assertEqual(history["stats"]["sessions"], 1)
        self.assertEqual(history["stats"]["matches"], 0)
        self.assertIsNone(history["stats"]["win_rate"])

    def test_unplayed_match_does_not_clutter_history(self):
        self.start()
        self.start(5)
        self.assertEqual(self.client.get("/api/history").json["records"], [])

    def test_storage_failure_warns_without_breaking_match(self):
        match = self.turn(self.start()).json["match"]
        with patch("rock_paper_scissors.web.HistoryStore.save", side_effect=StorageError("disk")):
            with self.assertLogs(self.app.logger, level="ERROR"):
                response = self.turn(match)
        self.assertTrue(response.json["match"]["finished"])
        self.assertIn("could not be saved", response.json["warning"])

    def test_unavailable_history_returns_json_error(self):
        with patch("rock_paper_scissors.web.HistoryStore.load", side_effect=StorageError("disk")):
            with self.assertLogs(self.app.logger, level="ERROR"):
                response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 503)
        self.assertIn("History is unavailable", response.json["error"])

    def test_payload_size_is_limited(self):
        response = self.post("/api/matches", {"player": "x" * 5000})
        self.assertEqual(response.status_code, 413)

    def test_untrusted_host_is_rejected(self):
        response = self.client.get("/api/state", headers={"Host": "untrusted.example"})
        self.assertEqual(response.status_code, 400)
