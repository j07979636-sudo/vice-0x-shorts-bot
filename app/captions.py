
"""VICE_0X caption generation module.

Creates short, readable caption lines for vertical videos.
"""

import re


class CaptionError(Exception):
    """Raised when caption generation fails."""


def create_captions(
    text: str,
    max_length: int = 42,
) -> list[str]:
    """Split text into readable caption lines."""

    if not isinstance(text, str) or not text.strip():
        raise CaptionError("Caption text cannot be empty.")

    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or max_length < 10
        or max_length > 100
    ):
        raise CaptionError(
            "Maximum length must be between 10 and 100."
        )

    text = re.sub(r"\s+", " ", text.strip())
    words = text.split(" ")

    captions = []
    current = ""

    for word in words:
        # Keep unusually long words intact instead of cutting them.
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
    
