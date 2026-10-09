"""Local development server entry point."""

import argparse
import threading
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

from . import __version__
from .web import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open Rock Paper Scissors in your browser.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--database", type=Path, help="Override the local SQLite history path")
    parser.add_argument("--version", action="version", version=f"rps-studio {__version__}")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    app = create_app(args.database.expanduser() if args.database else None)
    try:
        server = make_server("127.0.0.1", args.port, app, threaded=True)
    except SystemExit:
        return 1
    url = f"http://127.0.0.1:{args.port}"
    print(f"\nRock Paper Scissors · {url}\nPress Ctrl+C to stop.\n")
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nThanks for playing.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
