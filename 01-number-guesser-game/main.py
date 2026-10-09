"""Run the CLI directly from a checkout, without installing the package."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from number_guesser.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
