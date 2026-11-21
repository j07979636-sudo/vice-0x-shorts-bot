"""VICE_0X audio transcription module."""

from pathlib import Path


class TranscriptionError(Exception):
    """Raised when transcription fails."""


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using the configured transcription service.

    This is a placeholder until the cloud transcription provider
    is configured.
    """
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    raise TranscriptionError(
        "Transcription provider is not configured yet."
    )
  
