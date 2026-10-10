"""Extract from a bundled example, a local file, or a public URL."""

import argparse
from pathlib import Path


def main(argv=None):
    from scraper import extract_content, fetch_html, save_reports

    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Extract HTML content using a CSS selector."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--url", help="Full public page URL.")
    source.add_argument(
        "--file", type=Path, help="Read local HTML instead of using the internet."
    )
    parser.add_argument("--selector", default=".league-standing")
    parser.add_argument("--output", type=Path, default=root / "output")
    args = parser.parse_args(argv)
    try:
        if args.url:
            html = fetch_html(args.url)
        else:
            file = args.file or root / "sample.html"
            if file.stat().st_size > 2_000_000:
                raise ValueError("Use an HTML file smaller than 2 MB.")
            html = file.read_text(encoding="utf-8")
            if not args.file:
                print(
                    (
                        "Extracting the bundled fictional example. Use --url for a "
                        "live page."
                    )
                )
        results = extract_content(html, args.selector, args.url or "")
        for path in save_reports(results, args.output):
            print(f"Saved {path.resolve()}")
        print(f"Extracted {len(results)} matching elements (maximum 100).")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Could not extract content: {error}")
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 0


if __name__ == "__main__":
    import os
    import sys

    project = Path(__file__).resolve().parent
    environment = project / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(
            str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    raise SystemExit(main())
