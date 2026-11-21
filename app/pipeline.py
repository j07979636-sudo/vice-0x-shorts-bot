
"""VICE_0X automated Shorts processing pipeline."""

from pathlib import Path

from app.captions import create_captions
from app.editor import edit_short, validate_video
from app.limits import consume, LimitExceeded
from app.seo import generate_seo
from app.transcribe import transcribe_audio
from app.youtube import upload_video


class PipelineError(Exception):
    """Raised when pipeline processing fails."""


def _get_upload_metadata(seo: dict, topic: str) -> tuple:
    """Prepare safe YouTube metadata from SEO output."""

    if not isinstance(seo, dict):
        raise PipelineError("SEO generator returned invalid metadata.")

    title = seo.get("title") or topic
    description = seo.get("description") or topic

    tags = seo.get("tags", [])

    if not tags:
        tags = seo.get("hashtags", [])

    if isinstance(tags, str):
        tags = tags.split()

    if not isinstance(tags, list):
        tags = []

    clean_tags = [
        tag.strip().lstrip("#")
        for tag in tags
        if isinstance(tag, str) and tag.strip()
    ]

    return title, description, clean_tags


def process_video(
    video_path: str,
    topic: str,
    output_path: str | None = None,
) -> dict:
    """Process a video and upload the finished Short to YouTube."""

    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Video topic cannot be empty.")

    try:
        source = validate_video(video_path)

        output_dir = Path("/tmp/vice0x-data/processed")

        if output_path is None:
            output_dir.mkdir(parents=True, exist_ok=True)
            destination = output_dir / f"{source.stem}_short.mp4"
        else:
            destination = Path(output_path).expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)

        if source.resolve() == destination.resolve():
            raise PipelineError(
                "Input and output files must be different."
            )

        if destination.suffix.lower() != ".mp4":
            raise PipelineError("Output must use the .mp4 format.")

        consume("ai_calls")

        transcript = transcribe_audio(str(source))

        if not transcript.strip():
            raise PipelineError(
                "No speech was detected in the video."
            )

        captions = create_captions(transcript)
        seo = generate_seo(topic.strip())

        rendered_video = edit_short(
            str(source),
            str(destination),
        )

        rendered_path = Path(rendered_video)

        if not rendered_path.is_file():
            raise PipelineError(
                "Video editor did not create the output file."
            )

        title, description, tags = _get_upload_metadata(
            seo,
            topic.strip(),
        )

        upload_result = upload_video(
            video_path=str(rendered_path),
            title=title,
            description=description,
            tags=tags,
        )

        return {
            "original_video": str(source.resolve()),
            "processed_video": str(rendered_path.resolve()),
            "topic": topic.strip(),
            "transcript": transcript,
            "captions": captions,
            "seo": seo,
            "youtube": upload_result,
            "youtube_url": upload_result["url"],
            "youtube_video_id": upload_result["video_id"],
            "privacy": "unlisted",
            "status": "uploaded",
        }

    except LimitExceeded:
        raise

    except (FileNotFoundError, ValueError, PipelineError):
        raise

    except Exception as exc:
        raise PipelineError(
            f"Video processing or upload failed: {exc}"
        ) from exc
        
