
"""VICE_0X audio transcription module."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel


class TranscriptionError(Exception):
    """Raised when transcription fails."""


SUPPORTED_FORMATS = {
    ".mp3", ".wav", ".aac", ".m4a",
    ".mp4", ".mov", ".mkv", ".webm",
}

_model = None


def validate_audio(audio_path: str) -> Path:
    """Validate audio or video input."""

    path = Path(audio_path)

    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise TranscriptionError("Unsupported media format.")

    return path


def get_model():
    """Load the transcription model only when needed."""

    global _model

    if _model is None:
        try:
            _model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8",
            )
        except Exception as exc:
            raise TranscriptionError(
                f"Could not load transcription model: {exc}"
            ) from exc

    return _model


def transcribe_audio(audio_path: str) -> str:
    """Convert speech into text using Faster-Whisper."""

    path = validate_audio(audio_path)

    if not shutil.which("ffmpeg"):
        raise TranscriptionError("FFmpeg is not installed.")

    try:
        model = get_model()

        segments, info = model.transcribe(
            str(path),
            beam_size=1,
            vad_filter=True,
        )

        transcript = " ".join(
            segment.text.strip() for segment in segments
        ).strip()

        if not transcript:
            raise TranscriptionError("No speech detected.")

        return transcript

    except TranscriptionError:
        raise

    except Exception as exc:
        raise TranscriptionError(
            f"Transcription failed: {exc}"
        ) from exc
        
