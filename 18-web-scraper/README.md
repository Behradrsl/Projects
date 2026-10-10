# Web Scraper

Extract selected content from an HTML page and save readable HTML and JSON reports. Use a public URL or a local HTML file.

## Run it

Requires **Python 3.10 or newer**.

```bash
cd 18-web-scraper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The launcher uses this project’s `.venv` when it exists.

In VS Code, open **main.py** and choose **Run Python File in Terminal**. Use `Ctrl+C` to exit.

## Try the local example

`python main.py` extracts the table from the bundled **fictional league standings**. It creates `output/results.html` and `output/results.json`; open the HTML file in a browser.

To use another file or a live page:

```bash
python main.py --file page.html --selector "table"
python main.py --url "https://www.python.org/" --selector "h1" --output output/python
```

CSS selectors identify the elements to extract: `h1`, `table`, `.league-standing`, or `#content`. Inspect the page HTML to choose a selector that actually exists. A failed match explains what to change instead of producing an empty report.

## How it works

`scraper.py` uses Requests for public HTML and BeautifulSoup for CSS selection. For live pages it checks `robots.txt`, rejects disallowed paths, and asks you to use the final URL when a redirect occurs. Network or access failures produce a readable error; the app does not bypass blocked pages.

The reports contain text, table rows, and HTTP(S) links. Output HTML is rebuilt from escaped text, so page scripts and event handlers are not carried over. `main.py` chooses the source and writes both files.

The tool reads server-returned HTML; it does not execute JavaScript. Pages rendered entirely in a browser may need a different source. HTML is limited to 2 MB and output to 100 matched elements. Running again in the same output folder replaces the two reports.

Tests cover table extraction, relative links, selector errors, script removal, robots rules, size limits, and default execution from another folder.

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

GitHub Actions runs the tests and style checks on Python 3.10 and 3.13.
