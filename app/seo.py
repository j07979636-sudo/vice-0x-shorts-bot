"""VICE_0X YouTube Shorts SEO module."""

import re

DEFAULT_BRAND = "VICE_0X"


def clean_text(text: str) -> str:
    """Remove unnecessary spaces and line breaks."""

    if not isinstance(text, str):
        raise ValueError("Topic must be text.")

    return re.sub(r"\s+", " ", text).strip()


def generate_seo(topic: str) -> dict:
    """Generate YouTube Shorts title, description and tags."""

    topic = clean_text(topic)

    if not topic:
        raise ValueError("Video topic cannot be empty.")

    if len(topic) > 150:
        raise ValueError("Topic must be 150 characters or less.")

    title = f"{topic} 🔥 | {DEFAULT_BRAND} #shorts"

    hashtags = [
        "#shorts",
        "#gaming",
        "#gtavi",
        "#VICE0X",
    ]

    description = (
        f"{topic}\n\n"
        "Watch more gaming moments on VICE_0X!\n"
        "Subscribe for more gaming Shorts.\n\n"
        + " ".join(hashtags)
    )

    tags = [
        "GTA 6",
        "GTA VI",
        "gaming shorts",
        "VICE_0X",
        "viral gaming",
        "gaming highlights",
        "YouTube shorts",
    ]

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
    }
    
