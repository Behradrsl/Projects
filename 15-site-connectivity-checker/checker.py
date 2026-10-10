"""Check HTTP responses concurrently without downloading entire pages."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from time import perf_counter
from urllib.parse import urlsplit, urlunsplit

import requests


@dataclass(frozen=True)
class SiteResult:
    url: str
    status: str
    code: int | None
    milliseconds: float
    detail: str

    def as_dict(self):
        return asdict(self)


def normalize_url(text: str) -> str:
    text = text.strip()
    if "://" not in text:
        text = "https://" + text
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError as error:
        raise ValueError("Enter a valid website URL.") from error
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or any(c.isspace() for c in text)
    ):
        raise ValueError(
            "Use an http:// or https:// website without embedded credentials."
        )
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("The URL port must be between 1 and 65535.")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, "")
    )


def check_site(url: str, timeout=8) -> SiteResult:
    url = normalize_url(url)
    start = perf_counter()
    try:
        with requests.get(
            url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
            headers={"User-Agent": "PortfolioSiteChecker/1.0"},
        ) as response:
            code = response.status_code
            status = "Reachable" if 200 <= code < 400 else "HTTP error"
            detail = response.url
    except requests.Timeout:
        status, code, detail = "Timed out", None, "No response within the timeout."
    except requests.RequestException:
        status, code, detail = (
            "Connection error",
            None,
            "Could not connect. Check the URL, network, or TLS certificate.",
        )
    return SiteResult(
        url, status, code, round((perf_counter() - start) * 1000, 1), detail
    )


def check_sites(urls: list[str]) -> list[SiteResult]:
    if not 1 <= len(urls) <= 20:
        raise ValueError("Check between 1 and 20 URLs at a time.")
    normalized = list(dict.fromkeys(normalize_url(url) for url in urls))
    with ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(check_site, normalized))
