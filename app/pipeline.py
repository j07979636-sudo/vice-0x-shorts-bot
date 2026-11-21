
"""VICE_0X automated Shorts processing pipeline."""

from pathlib import Path

from app.captions import create_captions
from app.seo import generate_seo


class PipelineError(Exception):
    """Raised when pipeline processing fails."""


def process_video(video_path: str, topic: str) -> dict:
    """Validate input and prepare metadata for a Shorts workflow."""

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if not topic.strip():
        raise ValueError("Video topic cannot be empty.")

    seo = generate_seo(topic)
    captions = create_captions(topic)

    return {
        "video_path": str(path),
        "topic": topic,
        "captions": captions,
        "seo": seo,
        "status": "prepared",
    }
  
