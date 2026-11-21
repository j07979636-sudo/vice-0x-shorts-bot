
"""VICE_0X YouTube upload module."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.limits import consume


class YouTubeUploadError(Exception):
    """Raised when YouTube upload fails."""


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def check_youtube_credentials() -> bool:
    """Check whether OAuth credentials are configured."""

    required = (
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
    )

    return all(os.getenv(key, "").strip() for key in required)


def get_youtube_service():
    """Authenticate and create a YouTube API service."""

    if not check_youtube_credentials():
        raise YouTubeUploadError(
            "YouTube OAuth credentials are not configured."
        )

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )

    try:
        credentials.refresh(Request())

        return build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    except Exception as exc:
        raise YouTubeUploadError(
            "YouTube authentication failed. Check OAuth credentials."
        ) from exc


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
) -> dict:
    """Upload an authorized video to YouTube as Unlisted."""

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if path.suffix.lower() != ".mp4":
        raise ValueError("Only MP4 videos are supported.")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Video title cannot be empty.")

    if not isinstance(description, str):
        raise ValueError("Description must be text.")

    if tags is not None and not all(
        isinstance(tag, str) and tag.strip() for tag in tags
    ):
        raise ValueError("Every tag must be non-empty text.")

    if not check_youtube_credentials():
        raise YouTubeUploadError(
            "YouTube credentials are not configured."
        )

    service = get_youtube_service()

    clean_tags = [
        tag.strip()[:100]
        for tag in (tags or [])[:30]
    ]

    body = {
        "snippet": {
            "title": title.strip()[:100],
            "description": description[:5000],
            "tags": clean_tags,
            "categoryId": os.getenv("YOUTUBE_CATEGORY_ID", "20"),
        },
        "status": {
            "privacyStatus": "unlisted",
        },
    }

    try:
        consume("youtube_uploads")

        media = MediaFileUpload(
            str(path),
            mimetype="video/mp4",
            chunksize=8 * 1024 * 1024,
            resumable=True,
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None

        while response is None:
            _, response = request.next_chunk(num_retries=5)

        video_id = response.get("id")

        if not video_id:
            raise YouTubeUploadError(
                "YouTube did not return a video ID."
            )

        return {
            "video_id": video_id,
            "status": "uploaded",
            "privacy": "unlisted",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

    except HttpError as exc:
        raise YouTubeUploadError(
            f"YouTube API error: {exc}"
        ) from exc

    except YouTubeUploadError:
        raise

    except Exception as exc:
        raise YouTubeUploadError(
            f"Upload failed: {exc}"
        ) from exc
        
