"""Start the browser interface from a checkout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from rock_paper_scissors.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
