
"""VICE_0X scheduling module.

Validates future upload schedules and stores jobs
in the persistent SQLite queue.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.worker import add_job


class SchedulerError(Exception):
    """Raised when scheduling fails."""


SUPPORTED_VIDEO_FORMATS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".m4v",
}


def schedule_upload(
    video_path: str,
    scheduled_time: str,
) -> dict:
    """Validate and save a future upload schedule."""

    if not isinstance(video_path, str) or not video_path.strip():
        raise SchedulerError("A valid video path is required.")

    path = Path(video_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    if path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
        raise SchedulerError("Unsupported video format.")

    if not isinstance(scheduled_time, str) or not scheduled_time.strip():
        raise SchedulerError("A scheduled date/time is required.")

    try:
        scheduled = datetime.fromisoformat(
            scheduled_time.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise SchedulerError(
            "Invalid date/time. Use ISO 8601 format."
        ) from exc

    if scheduled.tzinfo is None or scheduled.utcoffset() is None:
        raise SchedulerError(
            "Timezone is required. Example: 2026-12-25T18:30:00+05:30"
        )

    scheduled_utc = scheduled.astimezone(timezone.utc)

    if scheduled_utc <= datetime.now(timezone.utc):
        raise SchedulerError("Schedule must be in the future.")

    resolved_path = str(path.resolve())

    try:
        job_id = add_job(
            video_path=resolved_path,
            scheduled_time=scheduled_utc.isoformat(),
        )
    except (ValueError, OSError) as exc:
        raise SchedulerError(
            f"Could not save scheduled job: {exc}"
        ) from exc

    return {
        "job_id": job_id,
        "video_path": resolved_path,
        "scheduled_time": scheduled_utc.isoformat(),
        "status": "scheduled_pending",
    }
    
