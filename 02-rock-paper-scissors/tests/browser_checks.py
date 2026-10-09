"""Real browser checks. Run separately: python tests/browser_checks.py.

Install the dev extra and Chromium first. Set RPS_BROWSER_CHANNEL=chrome to use
an installed Chrome instead. RPS_CAPTURE=1 also refreshes README screenshots.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from rock_paper_scissors.game import Move
from rock_paper_scissors.web import create_app


class BrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            channel=os.environ.get("RPS_BROWSER_CHANNEL"),
            headless=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        app = create_app(Path(self.directory.name) / "history.sqlite3")
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.random = patch("rock_paper_scissors.web.secrets.choice", return_value=Move.SCISSORS)
        self.random.start()
        self.addCleanup(self.random.stop)
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1100})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(f"http://127.0.0.1:{self.server.server_port}")
        expect(self.page.locator('[data-move="rock"]')).to_be_enabled()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def pick(self, move):
        self.page.locator(f'[data-move="{move}"]').click()
        expect(self.page.locator(".arena")).to_have_attribute("aria-busy", "false")

    def test_desktop_match_history_and_replay(self):
        if os.environ.get("RPS_CAPTURE"):
            path = Path(__file__).resolve().parents[1] / "docs" / "desktop.png"
            path.parent.mkdir(exist_ok=True)
            self.page.screenshot(path=path, full_page=True)
        self.pick("rock")
        expect(self.page.locator("#player-score")).to_have_text("1")
        self.pick("rock")
        expect(self.page.locator("#result-title")).to_have_text("The match is yours.")
        expect(self.page.locator('[data-move="rock"]')).to_be_disabled()
        self.page.get_by_role("button", name="History", exact=True).click()
        expect(self.page.locator("#stat-matches")).to_have_text("1")
        expect(self.page.locator("#stat-rate")).to_have_text("100%")
        expect(self.page.get_by_role("cell", name="WON", exact=True)).to_be_visible()
        self.page.get_by_role("button", name="Back to the game").click()
        self.page.get_by_role("button", name="Play again").click()
        expect(self.page.locator("#player-score")).to_have_text("0")
        expect(self.page.locator('[data-move="rock"]')).to_be_enabled()

    def test_free_play_draw_keyboard_rules_and_refresh(self):
        self.page.get_by_role("button", name="Free play", exact=True).click()
        expect(self.page.locator("#match-label")).to_have_text("FREE PLAY")
        self.page.locator("#player-name").fill("Ada")
        self.page.locator("#player-name").press("r")
        expect(self.page.locator("#round-count")).to_have_text("0")
        self.page.locator("#page-heading").click()
        self.page.keyboard.press("s")
        expect(self.page.locator("#draw-count")).to_have_text("1 draw")
        self.page.reload()
        expect(self.page.locator("#draw-count")).to_have_text("1 draw")
        self.page.get_by_role("button", name="How to play").click()
        expect(self.page.get_by_role("dialog")).to_be_visible()
        self.page.keyboard.press("r")
        expect(self.page.locator("#round-count")).to_have_text("1")
        self.page.keyboard.press("Escape")
        expect(self.page.get_by_role("dialog")).not_to_be_visible()
        self.page.get_by_role("button", name="Finish & save session").click()
        expect(self.page.locator("#result-title")).to_have_text("Evenly matched.")
        self.page.get_by_role("button", name="History", exact=True).click()
        expect(self.page.get_by_role("cell", name="Free play", exact=True)).to_be_visible()
        expect(self.page.locator("#stat-rate")).to_have_text("—")

    def test_format_change_confirmation_can_be_cancelled(self):
        self.pick("rock")
        self.page.once("dialog", lambda dialog: dialog.dismiss())
        self.page.get_by_role("button", name="Best of 5", exact=True).click()
        expect(self.page.locator("#match-label")).to_have_text("BEST OF 3")
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.get_by_role("button", name="Best of 5", exact=True).click()
        expect(self.page.locator("#match-label")).to_have_text("BEST OF 5")
        expect(self.page.locator("#player-score")).to_have_text("0")

    def test_mobile_layout_play_and_history(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.reload()
        expect(self.page.locator('[data-move="rock"]')).to_be_enabled()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        if os.environ.get("RPS_CAPTURE"):
            path = Path(__file__).resolve().parents[1] / "docs" / "mobile.png"
            path.parent.mkdir(exist_ok=True)
            self.page.screenshot(path=path, full_page=True, animations="disabled")
        self.pick("paper")
        expect(self.page.locator("#computer-score")).to_have_text("1")
        self.page.get_by_role("button", name="History", exact=True).click()
        expect(self.page.get_by_text("Every rivalry starts somewhere.")).to_be_visible()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)

    def test_reduced_motion_and_player_name_is_rendered_as_text(self):
        self.page.emulate_media(reduced_motion="reduce")
        self.page.locator("#player-name").fill("<b>Ada</b>")
        self.page.get_by_role("button", name="New match", exact=False).click()
        expect(self.page.locator("#player-label")).to_have_text("<b>Ada</b>")
        expect(self.page.locator("#player-label b")).to_have_count(0)
        self.pick("rock")
        self.pick("rock")
        self.page.get_by_role("button", name="History", exact=True).click()
        expect(self.page.get_by_role("cell", name="<b>Ada</b>", exact=True)).to_be_visible()


if __name__ == "__main__":
    unittest.main(verbosity=2)
