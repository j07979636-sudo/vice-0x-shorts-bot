
"""VICE_0X automated Shorts processing pipeline."""

from pathlib import Path

from app.captions import create_captions
from app.seo import generate_seo
from app.limits import consume, LimitExceeded


class PipelineError(Exception):
    """Raised when pipeline processing fails."""


def process_video(video_path: str, topic: str) -> dict:
    """Validate video and prepare Shorts metadata."""

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if not path.suffix.lower() in {
        ".mp4", ".mov", ".mkv", ".webm", ".m4v"
    }:
        raise PipelineError("Unsupported video format.")

    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Video topic cannot be empty.")

    try:
        consume("ai_calls")

        captions = create_captions(topic.strip())
        seo = generate_seo(topic.strip())

        return {
            "video_path": str(path),
            "topic": topic.strip(),
            "captions": captions,
            "seo": seo,
            "status": "prepared",
        }

    except LimitExceeded:
        raise

    except Exception as exc:
        raise PipelineError(
            f"Video preparation failed: {exc}"
        ) from exc
        
