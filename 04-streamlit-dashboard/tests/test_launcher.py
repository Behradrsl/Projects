"""The launcher chooses a usable interpreter and reports missing dependencies."""

import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from main import main


class LauncherTests(unittest.TestCase):
    def test_project_environment_is_used_and_options_are_forwarded(self):
        with patch("main.Path.is_file", return_value=True):
            with patch("main.subprocess.run", return_value=Mock(returncode=0)) as run:
                self.assertEqual(main(["--server.port", "8504"]), 0)
        command = run.call_args_list[1].args[0]
        self.assertIn(".venv", command[0])
        self.assertEqual(command[1:4], ["-m", "streamlit", "run"])
        self.assertEqual(command[-2:], ["--server.port", "8504"])
        self.assertIn("cwd", run.call_args_list[1].kwargs)

    def test_current_python_is_used_without_a_project_environment(self):
        with patch("main.Path.is_file", return_value=False):
            with patch("main.subprocess.run", return_value=Mock(returncode=0)) as run:
                self.assertEqual(main([]), 0)
        self.assertEqual(run.call_args_list[1].args[0][0], sys.executable)

    def test_missing_streamlit_provides_instructions_without_launching(self):
        output = io.StringIO()
        with patch("main.subprocess.run", return_value=Mock(returncode=1)) as run:
            with redirect_stdout(output):
                self.assertEqual(main([]), 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn("pip install -r requirements.txt", output.getvalue())


if __name__ == "__main__":
    unittest.main()
