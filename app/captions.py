
"""VICE_0X caption and subtitle generation module."""

import re
from pathlib import Path


class CaptionError(Exception):
    """Raised when caption generation fails."""


def create_captions(
    text: str,
    max_length: int = 42,
) -> list[str]:
    """Split transcript into readable caption lines."""

    if not isinstance(text, str) or not text.strip():
        raise CaptionError("Caption text cannot be empty.")

    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or not 10 <= max_length <= 100
    ):
        raise CaptionError(
            "Maximum length must be between 10 and 100."
        )

    text = re.sub(r"\s+", " ", text.strip())
    words = text.split()

    captions = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                captions.append(current)

            current = word

    if current:
        captions.append(current)

    return captions


def format_timestamp(seconds: float) -> str:
    """Convert seconds into SRT timestamp format."""

    milliseconds = max(0, round(seconds * 1000))

    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, milliseconds = divmod(remainder, 1000)

    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:02},{milliseconds:03}"
    )


def create_srt(
    text: str,
    duration: float,
    output_path: str,
    max_length: int = 42,
) -> str:
    """Create an SRT subtitle file with estimated timings."""

    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise CaptionError("Duration must be a number.")

    if duration <= 0:
        raise CaptionError("Duration must be positive.")

    captions = create_captions(text, max_length)

    if not captions:
        raise CaptionError("No captions could be generated.")

    total_words = sum(len(line.split()) for line in captions)
    current_time = 0.0
    subtitle_entries = []

    for index, line in enumerate(captions, start=1):
        word_count = len(line.split())

        segment_duration = duration * word_count / total_words

        start_time = current_time
        end_time = current_time + segment_duration

        if index == len(captions):
            end_time = float(duration)

        subtitle_entries.append(
            f"{index}\n"
            f"{format_timestamp(start_time)} --> "
            f"{format_timestamp(end_time)}\n"
            f"{line}\n"
        )

        current_time = end_time

    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        "\n".join(subtitle_entries),
        encoding="utf-8",
    )

    return str(destination.resolve())
        
