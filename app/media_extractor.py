"""Small FFmpeg wrapper for local media extraction."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FFmpegUnavailableError(RuntimeError):
    """Raised when FFmpeg is required but unavailable."""


def require_ffmpeg() -> str:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FFmpegUnavailableError(
            "ffmpeg was not found on this machine. Install ffmpeg or run without --video; "
            "teaching cards can still be generated from transcripts."
        )
    return ffmpeg_path


def extract_clip(video_path: str | Path, start_time: str, end_time: str, output_path: str | Path) -> Path:
    """Extract a clip between start_time and end_time."""
    ffmpeg = require_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-ss",
        start_time,
        "-to",
        end_time,
        "-i",
        str(video_path),
        "-c",
        "copy",
        str(output),
    ]
    _run_ffmpeg(command)
    return output


def extract_screenshot(video_path: str | Path, timestamp: str, output_path: str | Path) -> Path:
    """Extract a single screenshot at timestamp."""
    ffmpeg = require_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-ss",
        timestamp,
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output),
    ]
    _run_ffmpeg(command)
    return output


def _run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")
