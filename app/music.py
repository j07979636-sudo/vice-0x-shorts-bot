
"""VICE_0X background music management module."""

from pathlib import Path


class MusicError(Exception):
    """Raised when music processing fails."""


SUPPORTED_FORMATS = {".mp3", ".wav", ".aac", ".m4a"}


def validate_music(music_path: str) -> Path:
    """Validate a background music file."""
    path = Path(music_path)

    if not path.is_file():
        raise FileNotFoundError(f"Music file not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise MusicError("Unsupported music format.")

    return path


def prepare_music(music_path: str) -> str:
    """Validate music before adding it to a video."""
    path = validate_music(music_path)

    return str(path)
  
