"""Start a video download from arguments or friendly terminal prompts."""

import argparse
import os
import sys
from pathlib import Path

from downloader import QUALITIES, download_video


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Download a single YouTube video with audio."
    )
    parser.add_argument(
        "url", nargs="?", help="YouTube video URL (quote it in your shell)."
    )
    parser.add_argument(
        "--quality",
        choices=QUALITIES,
        default="720",
        help="Maximum height, or best. Default: 720.",
    )
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parent / "downloads"
    )
    args = parser.parse_args(argv)
    try:
        url = args.url
        if not url:
            print("YouTube Downloader\nPaste a video URL, or q to quit.")
            url = input("Video URL: ").strip()
            if url.lower() == "q":
                return 0
        download_video(url, args.output, args.quality)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(error)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nDownload cancelled. Partial files can resume on the next run.")
        return 0


if __name__ == "__main__":
    project = Path(__file__).resolve().parent
    environment_bin = project / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    environment_python = environment_bin / (
        "python.exe" if os.name == "nt" else "python"
    )
    if environment_python.is_file():
        # Make this project's Python and installed command-line tools available.
        os.environ["PATH"] = (
            str(environment_bin) + os.pathsep + os.environ.get("PATH", "")
        )
        if Path(sys.prefix).resolve() != (project / ".venv").resolve():
            os.execv(
                str(environment_python),
                [str(environment_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            )
    raise SystemExit(main())
