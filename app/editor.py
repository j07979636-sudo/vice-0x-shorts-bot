"""VICE_0X video editing module.

Uses FFmpeg to convert authorized videos into vertical YouTube Shorts.
"""

import shutil
import subprocess
from pathlib import Path


class VideoEditorError(Exception):
    """Raised when video editing fails."""


SUPPORTED_FORMATS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
}


def validate_video(video_path: str) -> Path:
    """Validate that the input video exists and has a supported format."""

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise VideoEditorError("Unsupported video format.")

    return path


def edit_short(input_path: str, output_path: str) -> str:
    """Convert a video into a vertical 1080x1920 MP4 Short."""

    source = validate_video(input_path)
    destination = Path(output_path)

    if destination.suffix.lower() != ".mp4":
        raise VideoEditorError("Output file must use .mp4 format.")

    if source.resolve() == destination.resolve():
        raise VideoEditorError("Input and output files must be different.")

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise VideoEditorError(
            "FFmpeg is not installed. Install FFmpeg before editing."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(destination),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )

        if result.returncode != 0:
            raise VideoEditorError(
                f"FFmpeg rendering failed: {result.stderr[-1500:]}"
            )

        if not destination.is_file() or destination.stat().st_size == 0:
            raise VideoEditorError("Rendering failed: output file is empty.")

        return str(destination)

    except subprocess.TimeoutExpired as exc:
        raise VideoEditorError("Video rendering timed out.") from exc
        
