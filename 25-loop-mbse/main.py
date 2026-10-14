"""Launch the dashboard with this project's environment and working directory."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    interpreter = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = str(interpreter) if interpreter.exists() else sys.executable
    if python == sys.executable:
        installed = importlib.util.find_spec("streamlit") is not None
    else:
        installed = (
            subprocess.run([python, "-c", "import streamlit"], capture_output=True).returncode == 0
        )
    if not installed:
        print("Install the project dependencies first:")
        print("  python3 -m venv .venv")
        print("  .venv/bin/python -m pip install -r requirements.txt")
        print("On Windows, use .venv\\Scripts\\python.exe instead.")
        return 1
    try:
        return subprocess.call(
            [python, "-m", "streamlit", "run", str(ROOT / "app.py"), *sys.argv[1:]],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
