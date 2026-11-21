"""VICE_0X caption generation module."""

import re


class CaptionError(Exception):
    """Raised when caption generation fails."""


def create_captions(text: str, max_length: int = 42) -> list[str]:
    """Split text into short, readable caption lines."""

    if not text or not text.strip():
        raise ValueError("Caption text cannot be empty.")

    if max_length < 10:
        raise ValueError("Maximum length must be at least 10.")

    words = re.findall(r"\S+", text.strip())
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
  
