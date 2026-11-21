"""VICE_0X video editing module."""

from pathlib import Path


class VideoEditorError(Exception):
    """Raised when video editing fails."""


def validate_video(video_path: str) -> Path:
    """Validate that the input video exists."""
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    if path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
        raise VideoEditorError("Unsupported video format.")

    return path


def edit_short(input_path: str, output_path: str) -> str:
    """Prepare a video for Shorts editing.

    Rendering will be connected in the next development stage.
    """
    source = validate_video(input_path)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    raise VideoEditorError(
        f"Video validated: {source}. Rendering engine is not configured."
    )
  
