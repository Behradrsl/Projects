"""HTTP routes; the Python engine is the authority for moves and scores."""

import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from .game import Match, Move
from .storage import HistoryStore, StorageError


@dataclass
class ActiveMatch:
    game: Match
    player: str
    id: str = field(default_factory=lambda: secrets.token_hex(16))
    next_move: Move = field(default_factory=lambda: secrets.choice(tuple(Move)))
    revision: int = 0
    saved: bool = False
    touched: float = field(default_factory=time.monotonic)


def create_app(database: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        MAX_CONTENT_LENGTH=4096,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_NAME="rps_session",
        TRUSTED_HOSTS=["localhost", "127.0.0.1"],
    )
    store = HistoryStore(database or Path.home() / ".rps-studio" / "history.sqlite3")
    matches: dict[str, ActiveMatch] = {}
    lock = threading.RLock()

    def current() -> ActiveMatch | None:
        return matches.get(session.get("id"))

    def persist(active: ActiveMatch) -> str | None:
        if active.saved or not active.game.rounds or not active.game.finished:
            return None
        try:
            store.save(active.id, active.player, active.game)
            active.saved = True
        except StorageError:
            app.logger.exception("Could not save match")
            return "This match could not be saved. You can still keep playing."
        return None

    def state(active: ActiveMatch | None) -> dict | None:
        if active is None:
            return None
        game = active.game
        return dict(
            id=active.id,
            player=active.player,
            best_of=game.best_of,
            target=game.target,
            wins=game.wins,
            losses=game.losses,
            draws=game.draws,
            finished=game.finished,
            outcome=game.outcome,
            revision=active.revision,
            rounds=[
                dict(
                    number=r.number,
                    player=r.player,
                    computer=r.computer,
                    outcome=r.outcome,
                    explanation=r.explanation,
                )
                for r in game.rounds
            ],
        )

    @app.before_request
    def protect_mutations():
        if "id" not in session:
            session["id"] = secrets.token_hex(24)
            session["csrf"] = secrets.token_hex(24)
        if request.method == "POST":
            token = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(token.encode(), session["csrf"].encode()):
                return jsonify(error="Your session changed. Refresh the page and try again."), 403
            if not request.is_json:
                return jsonify(error="A JSON request is required."), 415
        with lock:
            cutoff = time.monotonic() - 86400
            for key in [k for k, v in matches.items() if v.touched < cutoff]:
                del matches[key]
            if current():
                current().touched = time.monotonic()

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        with lock:
            return jsonify(match=state(current()), csrf=session["csrf"])

    @app.post("/api/matches")
    def start_match():
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify(error="Expected a JSON object."), 400
        name = data.get("player", "Guest")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 24:
            return jsonify(error="Use a name with 1–24 characters."), 400
        name = name.strip()
        if not all(c.isprintable() for c in name):
            return jsonify(error="Use printable characters for your name."), 400
        game = Match(data.get("best_of", 3))
        with lock:
            active = current()
            warning = None
            if active and not active.game.finished:
                active.game.finish()
                warning = persist(active)
            active = ActiveMatch(game, name)
            matches[session["id"]] = active
            return jsonify(match=state(active), warning=warning)

    def validate_turn(data):
        active = current()
        if active is None:
            raise ValueError("Start a match first.")
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        if (
            data.get("match_id") != active.id
            or type(data.get("revision")) is not int
            or data["revision"] != active.revision
        ):
            return active, (
                jsonify(error="The match changed. Please try again.", match=state(active)),
                409,
            )
        return active, None

    @app.post("/api/play")
    def play():
        data = request.get_json()
        with lock:
            active, error = validate_turn(data)
            if error:
                return error
            try:
                move = Move(data.get("move"))
            except (ValueError, TypeError):
                raise ValueError("Choose rock, paper, or scissors.") from None
            active.game.play(move, active.next_move)
            active.revision += 1
            active.next_move = secrets.choice(tuple(Move))
            return jsonify(match=state(active), warning=persist(active))

    @app.post("/api/finish")
    def finish():
        with lock:
            active, error = validate_turn(request.get_json())
            if error:
                return error
            active.game.finish()
            active.revision += 1
            return jsonify(match=state(active), warning=persist(active))

    @app.get("/api/history")
    def history():
        try:
            records = store.load()
        except StorageError:
            app.logger.exception("Could not load history")
            return jsonify(error="History is unavailable. Your current match still works."), 503
        completed = [r for r in records if r["best_of"] is not None and r["outcome"] != "abandoned"]
        wins = sum(r["outcome"] == "win" for r in completed)
        return jsonify(
            records=records[:50],
            stats=dict(
                sessions=len(records),
                matches=len(completed),
                wins=wins,
                win_rate=round(100 * wins / len(completed)) if completed else None,
                rounds=sum(r["wins"] + r["losses"] + r["draws"] for r in records),
            ),
        )

    @app.errorhandler(ValueError)
    def bad_input(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    return app
