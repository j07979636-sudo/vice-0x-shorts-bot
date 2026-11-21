
"""VICE_0X automated Shorts processing pipeline."""

from pathlib import Path

from app.captions import create_captions
from app.editor import edit_short, validate_video
from app.limits import consume, LimitExceeded
from app.seo import generate_seo
from app.transcribe import transcribe_audio


class PipelineError(Exception):
    """Raised when pipeline processing fails."""


def process_video(
    video_path: str,
    topic: str,
    output_path: str | None = None,
) -> dict:
    """Transcribe, prepare metadata and render a vertical Short."""

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
            raise PipelineError("No speech was detected in the video.")

        captions = create_captions(transcript)
        seo = generate_seo(topic.strip())

        rendered_video = edit_short(
            str(source),
            str(destination),
        )

        return {
            "original_video": str(source.resolve()),
            "processed_video": rendered_video,
            "topic": topic.strip(),
            "transcript": transcript,
            "captions": captions,
            "seo": seo,
            "status": "prepared",
        }

    except LimitExceeded:
        raise

    except (FileNotFoundError, ValueError, PipelineError):
        raise

    except Exception as exc:
        raise PipelineError(
            f"Video processing failed: {exc}"
        ) from exc
        
