
"""VICE_0X background worker.

Processes scheduled jobs when they become due.
This worker does not upload videos automatically yet.
"""

import logging
import time
from datetime import datetime, timezone

from app.database import get_connection, initialize_database

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


def initialize_jobs_table():
    """Create the scheduled jobs table."""

    initialize_database()

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        connection.commit()


def add_job(video_path: str, scheduled_time: str) -> int:
    """Save a validated schedule to the database."""

    if not isinstance(video_path, str) or not video_path.strip():
        raise ValueError("A valid video path is required.")

    if not isinstance(scheduled_time, str) or not scheduled_time.strip():
        raise ValueError("A scheduled time is required.")

    try:
        scheduled = datetime.fromisoformat(
            scheduled_time.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("Invalid ISO 8601 scheduled time.") from exc

    if scheduled.tzinfo is None or scheduled.utcoffset() is None:
        raise ValueError("Scheduled time must include a timezone.")

    if scheduled.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError("Scheduled time must be in the future.")

    initialize_jobs_table()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scheduled_jobs
            (video_path, scheduled_time, status, created_at)
            VALUES (?, ?, 'pending', ?)
            """,
            (
                video_path.strip(),
                scheduled.astimezone(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_due_jobs() -> list[dict]:
    """Return jobs whose scheduled time has arrived."""

    initialize_jobs_table()
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM scheduled_jobs
            WHERE status = 'pending' AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            """,
            (now,),
        ).fetchall()

    return [dict(row) for row in rows]


def mark_job_status(job_id: int, status: str) -> None:
    """Update a job's status."""

    allowed = {"pending", "processing", "completed", "failed"}

    if status not in allowed:
        raise ValueError("Unsupported job status.")

    with get_connection() as connection:
        connection.execute(
            "UPDATE scheduled_jobs SET status = ? WHERE id = ?",
            (status, job_id),
        )
        connection.commit()


def run_worker():
    """Poll for due jobs without performing uploads yet."""

    initialize_jobs_table()
    logger.info("VICE_0X worker started.")

    while True:
        try:
            jobs = get_due_jobs()

            for job in jobs:
                logger.info(
                    "Due job found: id=%s video=%s",
                    job["id"],
                    job["video_path"],
                )

                # Processing and YouTube upload will be connected
                # after the queue and retry logic are tested.

        except Exception:
            logger.exception("Worker polling failed.")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
      
