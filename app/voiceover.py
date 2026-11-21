
"""VICE_0X voiceover generation module."""

import shutil
import subprocess
from pathlib import Path


class VoiceoverError(Exception):
    """Raised when voiceover generation fails."""


def generate_voiceover(text: str, output_path: str) -> str:
    """Generate speech using an installed Piper executable."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Voiceover text cannot be empty.")

    destination = Path(output_path)

    if destination.suffix.lower() != ".wav":
        raise VoiceoverError("Voiceover output must be a WAV file.")

    piper = shutil.which("piper")

    if not piper:
        raise VoiceoverError(
            "Piper TTS is not installed on this server."
        )

    model_path = Path("/models/en_US-lessac-medium.onnx")

    if not model_path.is_file():
        raise VoiceoverError(
            "Piper voice model is missing from /models."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        piper,
        "--model", str(model_path),
        "--output_file", str(destination),
    ]

    try:
        result = subprocess.run(
            command,
            input=text.strip(),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

        if result.returncode != 0:
            raise VoiceoverError(
                f"Voice generation failed: {result.stderr[-1000:]}"
            )

        if not destination.is_file() or destination.stat().st_size == 0:
            raise VoiceoverError("Generated voice file is empty.")

        return str(destination)

    except subprocess.TimeoutExpired as exc:
        raise VoiceoverError("Voice generation timed out.") from exc
        
