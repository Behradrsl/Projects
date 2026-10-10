"""Extract selected public page content and write inert HTML and JSON reports."""

import html
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError

USER_AGENT = "PortfolioWebScraper/1.0"


def validate_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or any(c.isspace() for c in url)
    ):
        raise ValueError("Use a full http:// or https:// URL without credentials.")
    return parsed


def fetch_html(url: str) -> str:
    parsed = validate_url(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers = {"User-Agent": USER_AGENT}
    try:
        robots = requests.get(origin + "/robots.txt", headers=headers, timeout=12)
        if robots.status_code in (401, 403):
            raise ValueError(
                "The site does not allow access to its robots instructions."
            )
        if robots.status_code == 200:
            rules = RobotFileParser()
            rules.parse(robots.text.splitlines())
            if not rules.can_fetch(USER_AGENT, url):
                raise ValueError("The site’s robots.txt disallows scraping this path.")
        elif robots.status_code != 404:
            raise ValueError(
                "Could not check the site’s robots.txt. Try a local HTML file."
            )
        with requests.get(
            url, headers=headers, timeout=15, stream=True, allow_redirects=False
        ) as response:
            if 300 <= response.status_code < 400:
                raise ValueError("This URL redirects. Use the final page URL directly.")
            response.raise_for_status()
            if "html" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("The URL did not return an HTML page.")
            chunks = []
            total = 0
            for chunk in response.iter_content(8192):
                total += len(chunk)
                if total > 2_000_000:
                    raise ValueError("The HTML page exceeds the 2 MB limit.")
                chunks.append(chunk)
            return b"".join(chunks).decode(
                response.encoding or "utf-8", errors="replace"
            )
    except requests.RequestException as error:
        raise RuntimeError(
            "Could not fetch the page. Check the URL, connection, or site access."
        ) from error


def extract_content(source: str, selector: str, base_url="") -> list[dict]:
    soup = BeautifulSoup(source, "html.parser")
    for node in soup(["script", "style", "iframe", "noscript"]):
        node.decompose()
    try:
        matches = soup.select(selector)
    except SelectorSyntaxError as error:
        raise ValueError("The CSS selector is not valid.") from error
    if not matches:
        raise ValueError(
            (
                "No elements match that selector. Inspect the page HTML or "
                "try another selector."
            )
        )
    results = []
    for element in matches[:100]:
        links = []
        anchors = element.find_all("a", href=True)
        if element.name == "a" and element.has_attr("href"):
            anchors.insert(0, element)
        for link in anchors:
            url = urljoin(base_url, link["href"])
            if urlsplit(url).scheme in ("http", "https"):
                links.append({"text": link.get_text(" ", strip=True), "url": url})
        rows = [
            [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            for row in element.find_all("tr")
        ]
        results.append(
            {
                "text": element.get_text(" ", strip=True),
                "rows": [row for row in rows if row],
                "links": links,
            }
        )
    return results


def save_reports(results: list[dict], output: Path) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path, html_path = output / "results.json", output / "results.html"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sections = []
    for record in results:
        text = f"<p>{html.escape(record['text'])}</p>"
        table = ""
        if record["rows"]:
            table = (
                "<table>"
                + "".join(
                    "<tr>"
                    + "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
                    + "</tr>"
                    for row in record["rows"]
                )
                + "</table>"
            )
        links = "".join(
            f'<p><a href="{html.escape(link["url"], quote=True)}">'
            f"{html.escape(link['text'] or link['url'])}</a></p>"
            for link in record["links"]
        )
        sections.append(f"<section>{text}{table}{links}</section>")
    document = (
        (
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta '
            'name="viewport" content="width=device-width,initial-scale=1"'
            "><title>Extracted page content</title><style>body{font:17px "
            "system-ui;max-width:850px;margin:3rem auto;padding:0 1rem;co"
            "lor:#25364a}table{border-collapse:collapse}td{padding:.5rem "
            "1rem;border:1px solid #b9c7d7}section{margin-bottom:2rem}a{o"
            "verflow-wrap:anywhere}</style><h1>Extracted page "
            "content</h1>"
        )
        + "".join(sections)
        + "</html>"
    )
    html_path.write_text(document, encoding="utf-8")
    return html_path, json_path
