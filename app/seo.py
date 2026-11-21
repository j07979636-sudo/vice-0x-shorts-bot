"""VICE_0X YouTube Shorts SEO module."""

import re


DEFAULT_BRAND = "VICE_0X"


def clean_text(text: str) -> str:
    """Remove unnecessary spaces and line breaks."""
    return re.sub(r"\s+", " ", text).strip()


def generate_seo(topic: str) -> dict:
    """Generate title, description, hashtags and tags."""

    topic = clean_text(topic)

    if not topic:
        raise ValueError("Video topic cannot be empty.")

    title = f"{topic} 🔥 | {DEFAULT_BRAND} #shorts"

    description = (
        f"{topic}\n\n"
        "Follow VICE_0X for more gaming Shorts!\n\n"
        "#shorts #gaming #gtavi #VICE0X"
    )

    hashtags = [
        "#shorts",
        "#gaming",
        "#gtavi",
        "#VICE0X",
    ]

    tags = [
        "GTA 6",
        "GTA VI",
        "gaming shorts",
        "VICE_0X",
        "viral gaming",
    ]

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }
  
