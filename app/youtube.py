"""VICE_0X YouTube upload module."""

import os


class YouTubeUploadError(Exception):
    """Raised when YouTube upload fails."""


def check_youtube_credentials() -> bool:
    """Check whether YouTube credentials are configured."""
    return bool(os.getenv("YOUTUBE_CLIENT_ID")) and bool(
        os.getenv("YOUTUBE_CLIENT_SECRET")
    )


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
) -> dict:
    """Upload a video after YouTube API integration is configured."""
    from pathlib import Path

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if not title.strip():
        raise ValueError("Video title cannot be empty.")

    if not check_youtube_credentials():
        raise YouTubeUploadError(
            "YouTube credentials are not configured."
        )

    raise YouTubeUploadError(
        "YouTube API integration is not configured yet."
    )
  
