"""Start the news review app with python main.py, including from an IDE."""

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    project = Path(__file__).resolve().parent
    environment_python = (
        project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    python = str(environment_python) if environment_python.is_file() else sys.executable
    check = subprocess.run([python, "-c", "import streamlit"], capture_output=True)
    if check.returncode:
        print("Streamlit is not installed in the news review app's Python environment.")
        print("From this project folder, run:")
        print(f'  "{python}" -m pip install -r requirements.txt')
        print("Then run python main.py again.")
        return 1
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = subprocess.run(
            [python, "-m", "streamlit", "run", str(project / "app.py"), *arguments],
            cwd=project,
        )
        return result.returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
