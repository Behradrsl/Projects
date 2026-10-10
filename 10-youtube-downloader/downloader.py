"""Download one YouTube video using yt-dlp."""

import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

QUALITIES = ("360", "480", "720", "1080", "best")


def validate_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise ValueError("Paste a full https:// YouTube video URL.")
    video_id = ""
    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/")
    elif host in (
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    ):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 2 and parts[0] in ("shorts", "embed", "live"):
                video_id = parts[1]
    if len(video_id) != 11 or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for c in video_id
    ):
        raise ValueError(
            "Use a YouTube video link, rather than a channel or playlist link."
        )
    return f"https://www.youtube.com/watch?v={video_id}"


def build_options(output: Path, quality="720") -> dict:
    if quality not in QUALITIES:
        raise ValueError("Choose 360, 480, 720, 1080, or best.")
    limit = "" if quality == "best" else f"[height<={quality}]"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            ffmpeg = get_ffmpeg_exe()
        except (ImportError, RuntimeError) as error:
            raise RuntimeError(
                "FFmpeg is missing. Run: python -m pip install -r requirements.txt"
            ) from error
    format_selector = f"bv*{limit}+ba/b{limit}"
    runtimes = {name: {} for name in ("deno", "node", "bun") if shutil.which(name)}
    return {
        "format": format_selector,
        "ffmpeg_location": ffmpeg,
        "outtmpl": str(output / "%(title).150B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "overwrites": False,
        "continuedl": True,
        "socket_timeout": 20,
        "retries": 3,
        "js_runtimes": runtimes,
    }


def download_video(url: str, output: Path, quality="720") -> None:
    url = validate_url(url)
    output = Path(output).expanduser().resolve()
    options = build_options(output, quality)
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError as error:
        raise RuntimeError(
            "yt-dlp is missing. Run: python -m pip install -r requirements.txt"
        ) from error
    if not options["js_runtimes"]:
        raise RuntimeError(
            "YouTube needs a JavaScript runtime. Install Deno, then try again. "
            "On macOS with Homebrew: brew install deno"
        )
    output.mkdir(parents=True, exist_ok=True)
    try:
        with YoutubeDL(options) as downloader:
            status = downloader.download([url])
        if status:
            raise RuntimeError(
                "The download did not complete. Check the message above."
            )
    except DownloadError as error:
        raise RuntimeError(
            f"Download failed: {error}\nCheck the URL and connection. "
            'Update yt-dlp: python -m pip install -U "yt-dlp[default]"'
        ) from error
    print(f"Download complete. Files are in {output}")
