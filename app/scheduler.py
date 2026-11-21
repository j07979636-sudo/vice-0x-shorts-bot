"""VICE_0X scheduling module."""

from datetime import datetime, timezone


class SchedulerError(Exception):
    """Raised when scheduling fails."""


def schedule_upload(
    video_path: str,
    scheduled_time: str,
) -> dict:
    """Validate and prepare a future upload schedule."""

    from pathlib import Path

    path = Path(video_path)

    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    try:
        scheduled = datetime.fromisoformat(scheduled_time)
    except ValueError as exc:
        raise SchedulerError(
            "Invalid date/time format. Use ISO 8601."
        ) from exc

    if scheduled.tzinfo is None:
        raise SchedulerError("Timezone information is required.")

    if scheduled <= datetime.now(timezone.utc):
        raise SchedulerError("Schedule must be in the future.")

    return {
        "video_path": str(path),
        "scheduled_time": scheduled.isoformat(),
        "status": "scheduled_pending",
    }
  
