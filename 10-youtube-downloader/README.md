# YouTube Downloader

Download one YouTube video with audio from a terminal. Choose a maximum resolution and an output folder; yt-dlp displays download progress and handles the media transfer.

## Set up

Requires **Python 3.10 or newer**, an internet connection, and a supported JavaScript runtime. [yt-dlp's documentation](https://github.com/yt-dlp/yt-dlp#dependencies) explains its YouTube runtime requirements.

```bash
cd 10-youtube-downloader
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.

Install [Deno](https://docs.deno.com/runtime/getting_started/installation/) if you do not already have Deno, Node.js, or Bun. On macOS with Homebrew:

```bash
brew install deno
```

The Python requirements install yt-dlp and a bundled FFmpeg executable through [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg). FFmpeg combines separate video and audio streams; an existing system installation is used when available. Deno is a separate program. Without a JavaScript runtime, the app explains what to install before attempting the download.

## Run it

```bash
python main.py
```

Paste a YouTube video URL when prompted, or type `q` to exit. You can also pass options directly:

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --quality 720
python main.py "https://youtu.be/VIDEO_ID" --quality best --output ~/Downloads/videos
```

Replace `VIDEO_ID` with the video's actual ID. Quote URLs so shell characters such as `&` are handled correctly. In VS Code, run **main.py** in the terminal. The launcher uses this project's `.venv` when present.

Quality options are `360`, `480`, `720`, `1080`, and `best`; the default is `720`. Numeric choices are maximum heights, so a lower-resolution video is still accepted. The output keeps the selected stream's format rather than forcing MP4.

Downloads go to this project's `downloads/` folder by default, with the video title and ID in the filename. Existing completed files are not overwritten. `Ctrl+C` cancels; running the same command again can resume a partial download. Playlist parameters are removed so a video link downloads only that video.

## How it works

`downloader.py` validates common YouTube video links and builds yt-dlp options. It selects video and audio streams up to the requested height and lets yt-dlp merge them with FFmpeg. Combined streams are accepted too. `main.py` handles prompts, command-line options, and readable errors.

Unavailable, private, restricted, or changed videos may fail. If YouTube changes its delivery system, update the dependency:

```bash
python -m pip install -U "yt-dlp[default]"
```

This tool does not sign in or bypass access restrictions. Download videos you own or have permission to save.

## Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
```

Tests cover URL validation, resolution selection, missing runtimes, download failures, and terminal usage. A local media fixture tests a real yt-dlp download without relying on YouTube's availability. Public YouTube access depends on your network and the video.
