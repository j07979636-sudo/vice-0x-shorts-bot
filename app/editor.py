
"""VICE_0X video editing module.

Converts authorized videos into vertical YouTube Shorts
and optionally burns subtitles into the video.
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
    """Validate that the input video exists and is supported."""

    path = Path(video_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise VideoEditorError("Unsupported video format.")

    return path.resolve()


def _escape_subtitle_path(path: Path) -> str:
    """Escape a subtitle path for the FFmpeg filter."""

    value = str(path.resolve())

    for char in ("\\", ":", "'", ",", "[", "]"):
        value = value.replace(char, "\\" + char)

    return value


def edit_short(
    input_path: str,
    output_path: str,
    subtitle_path: str | None = None,
) -> str:
    """Convert video to vertical MP4 and optionally burn subtitles."""

    source = validate_video(input_path)
    destination = Path(output_path).expanduser()

    if destination.suffix.lower() != ".mp4":
        raise VideoEditorError("Output file must use .mp4 format.")

    if source.resolve() == destination.resolve():
        raise VideoEditorError(
            "Input and output files must be different."
        )

    if subtitle_path is not None:
        subtitles = Path(subtitle_path).expanduser()

        if not subtitles.is_file():
            raise FileNotFoundError(
                f"Subtitle file not found: {subtitles}"
            )

        if subtitles.suffix.lower() != ".srt":
            raise VideoEditorError("Subtitle file must use .srt format.")

        subtitle_filter = (
            "subtitles=filename='"
            + _escape_subtitle_path(subtitles)
            + "':force_style='"
            "FontName=DejaVu Sans,"
            "FontSize=18,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=2,"
            "Shadow=1,"
            "Alignment=2,"
            "MarginV=150"
            "'"
        )

        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,"
            + subtitle_filter
        )

    else:
        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1"
        )

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise VideoEditorError(
            "FFmpeg is not installed."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
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
                "FFmpeg rendering failed: "
                + result.stderr[-1500:]
            )

        if (
            not destination.is_file()
            or destination.stat().st_size == 0
        ):
            raise VideoEditorError(
                "Rendering failed: output file is empty."
            )

        return str(destination.resolve())

    except subprocess.TimeoutExpired as exc:
        raise VideoEditorError(
            "Video rendering timed out."
        ) from exc
        
