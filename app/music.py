
"""VICE_0X background music processing module."""

import shutil
import subprocess
from pathlib import Path


class MusicError(Exception):
    """Raised when music processing fails."""


SUPPORTED_FORMATS = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}


def validate_music(music_path: str) -> Path:
    """Validate a background music file."""

    path = Path(music_path)

    if not path.is_file():
        raise FileNotFoundError(f"Music file not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise MusicError("Unsupported music format.")

    return path


def prepare_music(music_path: str, output_path: str | None = None) -> str:
    """Normalize music and optionally export it as an MP3 file."""

    source = validate_music(music_path)

    if output_path is None:
        return str(source)

    destination = Path(output_path)

    if destination.suffix.lower() != ".mp3":
        raise MusicError("Output file must use .mp3 format.")

    if source.resolve() == destination.resolve():
        raise MusicError("Input and output files must be different.")

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise MusicError("FFmpeg is not installed.")

    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-i", str(source),
        "-vn",
        "-af", "loudnorm",
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        str(destination),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        if result.returncode != 0:
            raise MusicError(
                f"Audio processing failed: {result.stderr[-1000:]}"
            )

        if not destination.is_file() or destination.stat().st_size == 0:
            raise MusicError("Audio output is empty.")

        return str(destination)

    except subprocess.TimeoutExpired as exc:
        raise MusicError("Audio processing timed out.") from exc
        
