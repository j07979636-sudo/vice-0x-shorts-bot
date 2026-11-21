
"""VICE_0X YouTube Shorts SEO module."""

import re

DEFAULT_BRAND = "VICE_0X"

STOP_WORDS = {
    "the", "and", "for", "with", "this", "that",
    "from", "your", "you", "are", "was", "how",
    "what", "when", "where", "why", "who",
}


def clean_text(text: str) -> str:
    """Remove unnecessary spaces and line breaks."""

    if not isinstance(text, str):
        raise ValueError("Topic must be text.")

    return re.sub(r"\s+", " ", text).strip()


def make_hashtag(text: str) -> str:
    """Convert text into a valid simple hashtag."""

    cleaned = re.sub(r"[^a-zA-Z0-9]", "", text)

    return f"#{cleaned}" if cleaned else ""


def generate_seo(topic: str) -> dict:
    """Generate topic-based YouTube Shorts metadata."""

    topic = clean_text(topic)

    if not topic:
        raise ValueError("Video topic cannot be empty.")

    if len(topic) > 150:
        raise ValueError("Topic must be 150 characters or less.")

    words = topic.split()

    title_topic = topic[:75].strip()

    title = f"{title_topic} 🔥 | {DEFAULT_BRAND} #Shorts"

    title = title[:100]

    topic_hashtag = make_hashtag(topic)

    hashtags = [
        "#Shorts",
        topic_hashtag,
        "#VICE0X",
    ]

    hashtags = list(dict.fromkeys(
        tag for tag in hashtags if tag
    ))

    description = (
        f"{topic}\n\n"
        f"Watch more videos on {DEFAULT_BRAND}!\n"
        "Subscribe for more interesting Shorts.\n\n"
        + " ".join(hashtags)
    )

    tags = [
        topic,
        f"{topic} shorts",
        f"{topic} highlights",
        "short videos",
        "YouTube Shorts",
        DEFAULT_BRAND,
    ]

    for word in words:
        normalized = word.lower()

        if normalized not in STOP_WORDS and len(normalized) > 2:
            tags.append(normalized)

    tags = list(dict.fromkeys(
        tag.strip() for tag in tags if tag.strip()
    ))[:30]

    return {
        "title": title,
        "description": description[:5000],
        "hashtags": hashtags,
        "tags": tags,
    }
    
