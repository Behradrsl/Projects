# Rock Paper Scissors

A browser-based Rock Paper Scissors game built with Python and Flask. Play against the computer, choose a match format, and keep a local history of your results.

The interface uses plain HTML, CSS, and JavaScript. Python handles the rules, computer moves, scores, and SQLite storage. No Node.js or frontend build step is required.

![Rock Paper Scissors desktop interface](docs/desktop.png)

<details>
<summary>Mobile preview</summary>

<img src="docs/mobile.png" width="320" alt="Rock Paper Scissors on a mobile screen">

</details>

## Requirements

- Python 3.10 or newer
- A modern browser with JavaScript enabled

## Installation and launch

Open a terminal in this project folder, `02-rock-paper-scissors`, where `main.py` and `pyproject.toml` are located.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The launcher starts the local server and opens **http://127.0.0.1:8000** in your browser. Keep the terminal running while you play. Press `Ctrl+C` in the terminal to stop the server.

Installing `requirements.txt` installs this project in editable mode and its Flask dependency. After installation, you can also launch it with either command:

```bash
rps
python -m rock_paper_scissors
```

### Launch options

| Option | Purpose | Default |
| --- | --- | --- |
| `--port PORT` | Choose a port from 1 to 65535 | `8000` |
| `--no-browser` | Start without opening a browser tab | Browser opens |
| `--database PATH` | Choose the SQLite history file | `~/.rps-studio/history.sqlite3` |
| `--version` | Print the installed app version and exit | — |

For example:

```bash
python main.py --port 8080 --no-browser --database ./data/history.sqlite3
```

Then open **http://127.0.0.1:8080** yourself. The same options work with `rps` and `python -m rock_paper_scissors`.

## How to play

A new browser session automatically starts a best-of-three match.

1. Choose **Best of 3**, **Best of 5**, **Best of 7**, or **Free play**.
2. Click a move, or press `R` for rock, `P` for paper, or `S` for scissors.
3. Watch the reveal and score update. Use **Play again** after a match ends.

Rock beats scissors, paper beats rock, and scissors beats paper. Identical moves are a draw.

| Format | Finish condition |
| --- | --- |
| Best of 3 | First to 2 wins |
| Best of 5 | First to 3 wins |
| Best of 7 | First to 4 wins |
| Free play | Continue until you choose **Finish & save session** |

Draws count as played rounds but do not advance the win target, so a best-of match can exceed its named number of rounds.

Use **Settings** to enter a player name of up to 24 characters and start a new match. The browser remembers the name for later visits. Keyboard move shortcuts pause while a dialog is open or you are typing in an input.

Use **History** to see saved results, statistics, and the latest five rounds of the current match. **How to play** opens the rules. The interface supports small screens, keyboard navigation, and reduced-motion preferences.

## Saving and restoring games

- Completed best-of matches save automatically.
- **End this match** ends a best-of match early and records it as unfinished.
- **Finish & save session** ends free play and saves its score as a win, loss, or tie.
- Starting a new match or changing formats ends the previous active session. If rounds have been played, the interface asks for confirmation first.
- Sessions with no played rounds are not saved.

History stores match summaries, rather than individual rounds. It shows the latest 50 saved sessions, with statistics calculated across all saved sessions. Match wins and win rate include only completed best-of matches; free play and unfinished matches are excluded. The rounds total includes all saved sessions.

The default database is `~/.rps-studio/history.sqlite3`. Its parent folder is created when needed. History is shared by all players using the same database; player names are labels, not accounts.

Refreshing the page restores the current match while the server is running. Active matches are held in memory and expire after 24 hours of inactivity. Closing a tab does not end or save an active match. Restarting the server clears active matches and browser sessions but preserves saved history.

## Project structure

```text
02-rock-paper-scissors/
├── README.md
├── main.py                       # Launch from a checkout
├── pyproject.toml                # Package metadata and dependencies
├── requirements.txt             # Editable installation of this project
├── LICENSE-TABLER.txt            # Icon license
├── docs/                        # README screenshots
├── src/rock_paper_scissors/
│   ├── __init__.py
│   ├── __main__.py               # Command-line options and local server
│   ├── game.py                   # Moves, round outcomes, and match rules
│   ├── storage.py                # SQLite match summaries
│   ├── web.py                    # Flask routes and session state
│   ├── templates/index.html      # Browser interface
│   └── static/                   # JavaScript, CSS, and favicon
└── tests/
    ├── test_game.py
    ├── test_storage.py
    ├── test_web.py
    └── browser_checks.py
```

The game engine has no Flask or database dependency. The server selects the computer's next move before the player submits theirs and checks match IDs and revisions to reject stale turns. SQLite saves each finished session under a unique ID to prevent duplicate records.

The launcher listens on `127.0.0.1` for local use. Active matches and session secrets live in one server process; a public deployment would require changes to server and session configuration.

## Development and checks

With your virtual environment active, install the development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the Python tests, lint, and formatting checks from this project folder:

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

The Python tests cover game rules, match formats, persistence, request validation, session isolation, and error handling.

To run the browser checks:

```bash
python -m playwright install chromium
python tests/browser_checks.py
```

These checks cover gameplay, replay, history, format-change confirmation, keyboard input, refresh recovery, mobile layout, reduced motion, and player-name rendering.

Optional environment variables for browser checks:

| Variable | Purpose |
| --- | --- |
| `RPS_BROWSER_CHANNEL=chrome` | Use an installed Chrome browser instead of Playwright's Chromium |
| `RPS_CAPTURE=1` | Update `docs/desktop.png` and `docs/mobile.png` while running the checks |

## Troubleshooting

- **Port 8000 is busy:** launch with `python main.py --port 8080`.
- **The browser did not open:** open the address printed in the terminal.
- **The page cannot reach the game:** check that the Python server is running, then refresh.
- **History cannot load or save:** check that the database path is writable and points to this app's database. Use `--database` to select a new file if necessary.
- **The package cannot be imported:** activate the virtual environment and run `python -m pip install -r requirements.txt` from this project folder.

## Credits

Based on the Pytopia Project-Based Python Rock Paper Scissors exercise.

The colored cartoon hand illustrations are custom SVG artwork based on the supplied visual reference. The project also retains the earlier Tabler icon license in [LICENSE-TABLER.txt](LICENSE-TABLER.txt).
