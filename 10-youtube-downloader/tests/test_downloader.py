import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yt_dlp
from yt_dlp.utils import DownloadError

from downloader import build_options, download_video, validate_url

ROOT = Path(__file__).resolve().parents[1]
VIDEO = "BaW_jenozKc"
URL = f"https://www.youtube.com/watch?v={VIDEO}"


class DownloaderTests(unittest.TestCase):
    def test_normalizes_video_links_and_avoids_playlists(self):
        for url in [
            URL,
            f"https://youtu.be/{VIDEO}?t=2",
            f"https://youtube.com/shorts/{VIDEO}",
            f"https://m.youtube.com/watch?v={VIDEO}&list=abc",
            f"https://youtube.com/live/{VIDEO}",
        ]:
            self.assertEqual(validate_url(url), URL)

    def test_rejects_invalid_or_other_site_links(self):
        for url in [
            "",
            "not a url",
            "https://youtube.com/playlist?list=abc",
            f"https://youtube.com.evil.org/watch?v={VIDEO}",
            "file:///tmp/video",
            "https://youtube.com/watch?v=short",
            f"https://user:secret@youtube.com/watch?v={VIDEO}",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_quality_cap_with_system_or_bundled_ffmpeg(self):
        for ffmpeg in (True, False):
            with (
                patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="/bundled/ffmpeg"),
                patch(
                    "downloader.shutil.which",
                    side_effect=lambda name: "/bin/" + name
                    if name == "deno" or ffmpeg and name == "ffmpeg"
                    else None,
                ),
            ):
                options = build_options(Path("/tmp/output"), "720")
                self.assertEqual(
                    options["format"],
                    "bv*[height<=720]+ba/b[height<=720]",
                )
                self.assertTrue(options["noplaylist"])
                self.assertFalse(options["overwrites"])
                self.assertEqual(options["js_runtimes"], {"deno": {}})
        with self.assertRaises(ValueError):
            build_options(Path("/tmp"), "invalid")

    @patch("downloader.shutil.which", return_value="/bin/tool")
    @patch("yt_dlp.YoutubeDL")
    def test_download_passes_validated_url_and_reports_failure(self, ydl, which):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "downloads"
            instance = ydl.return_value.__enter__.return_value
            instance.download.return_value = 0
            download_video(f"https://youtu.be/{VIDEO}", destination)
            instance.download.assert_called_once_with([URL])
            self.assertTrue(destination.is_dir())
            instance.download.return_value = 1
            with self.assertRaises(RuntimeError):
                download_video(URL, destination)
            instance.download.side_effect = DownloadError("Unavailable")
            with self.assertRaisesRegex(RuntimeError, "Download failed"):
                download_video(URL, destination)

    def test_missing_runtime_has_actionable_error(self):
        with patch("downloader.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Install Deno"):
                download_video(URL, Path("/tmp/unused-download"))

    def test_real_library_downloads_a_local_media_fixture(self):
        # Exercise yt-dlp itself without depending on YouTube or public networking.
        import functools
        import http.server
        import threading
        import wave

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / "sample.wav"
            with wave.open(str(source), "wb") as sound:
                sound.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                sound.writeframes(b"\0\0" * 800)
            handler = functools.partial(
                http.server.SimpleHTTPRequestHandler, directory=folder
            )
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with yt_dlp.YoutubeDL(
                    {"quiet": True, "outtmpl": str(folder / "copy.%(ext)s")}
                ) as ydl:
                    self.assertEqual(
                        ydl.download(
                            [f"http://127.0.0.1:{server.server_port}/sample.wav"]
                        ),
                        0,
                    )
                self.assertEqual(
                    (folder / "copy.wav").read_bytes(), source.read_bytes()
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_launcher_help_quit_and_invalid_url_from_another_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            for arguments, answers, expected in [
                (["--help"], "", 0),
                ([], "q\n", 0),
                (["https://example.com"], "", 1),
            ]:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "main.py"), *arguments],
                    input=answers,
                    text=True,
                    capture_output=True,
                    cwd=folder,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertNotIn("Traceback", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
