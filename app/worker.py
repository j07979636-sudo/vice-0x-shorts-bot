
"""VICE_0X background worker.

Processes scheduled videos and tracks YouTube upload results.
"""

import logging
import os
import re
import socket
import time

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.database import get_connection, initialize_database

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
JOB_TIMEOUT_MINUTES = 120
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


def initialize_jobs_table():
    """Create and migrate the scheduled jobs table."""

    initialize_database()

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                claimed_at TEXT,
                worker_id TEXT,
                error_message TEXT,
                processed_path TEXT,
                youtube_video_id TEXT,
                youtube_url TEXT
            )
        """)

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(scheduled_jobs)"
            ).fetchall()
        }

        migrations = {
            "claimed_at": "TEXT",
            "worker_id": "TEXT",
            "error_message": "TEXT",
            "processed_path": "TEXT",
            "youtube_video_id": "TEXT",
            "youtube_url": "TEXT",
        }

        for name, definition in migrations.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE scheduled_jobs ADD COLUMN {name} {definition}"
                )

        connection.commit()


def add_job(video_path: str, scheduled_time: str) -> int:
    """Save a future video-processing job."""

    if not isinstance(video_path, str) or not video_path.strip():
        raise ValueError("A valid video path is required.")

    if not isinstance(scheduled_time, str) or not scheduled_time.strip():
        raise ValueError("A scheduled time is required.")

    try:
        scheduled = datetime.fromisoformat(
            scheduled_time.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("Invalid ISO 8601 scheduled time.") from exc

    if scheduled.tzinfo is None or scheduled.utcoffset() is None:
        raise ValueError("Scheduled time must include a timezone.")

    scheduled = scheduled.astimezone(timezone.utc)

    if scheduled <= datetime.now(timezone.utc):
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
                str(Path(video_path).expanduser().resolve()),
                scheduled.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        connection.commit()
        return cursor.lastrowid


def claim_due_jobs(limit: int = 5) -> list[dict]:
    """Atomically claim due jobs."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Job limit must be a positive integer.")

    initialize_jobs_table()

    now = datetime.now(timezone.utc).isoformat()
    claimed = []

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        rows = connection.execute(
            """
            SELECT id
            FROM scheduled_jobs
            WHERE status = 'pending'
              AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()

        for row in rows:
            cursor = connection.execute(
                """
                UPDATE scheduled_jobs
                SET status = 'processing',
                    claimed_at = ?,
                    worker_id = ?,
                    error_message = NULL
                WHERE id = ?
                  AND status = 'pending'
                """,
                (now, WORKER_ID, row["id"]),
            )

            if cursor.rowcount == 1:
                job = connection.execute(
                    "SELECT * FROM scheduled_jobs WHERE id = ?",
                    (row["id"],),
                ).fetchone()

                claimed.append(dict(job))

        connection.commit()

    return claimed


def mark_job_status(
    job_id: int,
    status: str,
    error_message: str | None = None,
    processed_path: str | None = None,
    youtube_video_id: str | None = None,
    youtube_url: str | None = None,
):
    """Update job status and save upload information."""

    allowed = {"pending", "processing", "completed", "failed"}

    if status not in allowed:
        raise ValueError("Unsupported job status.")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE scheduled_jobs
            SET status = ?,
                error_message = ?,
                processed_path = COALESCE(?, processed_path),
                youtube_video_id = COALESCE(?, youtube_video_id),
                youtube_url = COALESCE(?, youtube_url),
                claimed_at = CASE
                    WHEN ? = 'processing' THEN claimed_at
                    ELSE NULL
                END,
                worker_id = CASE
                    WHEN ? = 'processing' THEN worker_id
                    ELSE NULL
                END
            WHERE id = ?
            """,
            (
                status,
                error_message[:1000] if error_message else None,
                processed_path,
                youtube_video_id,
                youtube_url,
                status,
                status,
                job_id,
            ),
        )

        connection.commit()


def recover_stale_jobs():
    """Requeue jobs abandoned beyond the timeout."""

    initialize_jobs_table()

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(minutes=JOB_TIMEOUT_MINUTES)
    ).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE scheduled_jobs
            SET status = 'pending',
                claimed_at = NULL,
                worker_id = NULL,
                error_message = 'Recovered after worker timeout'
            WHERE status = 'processing'
              AND claimed_at IS NOT NULL
              AND claimed_at <= ?
            """,
            (cutoff,),
        )

        connection.commit()
        return cursor.rowcount


def process_job(job: dict):
    """Process a video and upload the finished Short."""

    job_id = job["id"]
    source = Path(job["video_path"])

    try:
        if not source.is_file():
            raise FileNotFoundError(
                f"Scheduled video no longer exists: {source}"
            )

        topic = re.sub(r"[_-]+", " ", source.stem).strip()

        if not topic:
            topic = "Gaming Shorts"

        output_dir = Path(settings.data_dir) / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"job_{job_id}_short.mp4"

        from app.pipeline import process_video

        result = process_video(
            video_path=str(source),
            topic=topic,
            output_path=str(output_path),
        )

        rendered = Path(result["processed_video"])

        if not rendered.is_file() or rendered.stat().st_size == 0:
            raise RuntimeError("Pipeline did not produce a valid video.")

        youtube = result.get("youtube")

        if not isinstance(youtube, dict):
            raise RuntimeError("YouTube upload result is missing.")

        video_id = youtube.get("video_id")
        video_url = youtube.get("url")

        if not video_id or not video_url:
            raise RuntimeError("YouTube upload confirmation is incomplete.")

        mark_job_status(
            job_id,
            "completed",
            processed_path=str(rendered.resolve()),
            youtube_video_id=video_id,
            youtube_url=video_url,
        )

        logger.info(
            "Job %s uploaded successfully: %s",
            job_id,
            video_url,
        )

    except Exception as exc:
        logger.exception("Job %s failed.", job_id)

        mark_job_status(
            job_id,
            "failed",
            error_message=str(exc),
        )


def run_worker():
    """Continuously process due jobs."""

    initialize_jobs_table()

    recovered = recover_stale_jobs()

    logger.info(
        "VICE_0X worker started. Recovered jobs: %s",
        recovered,
    )

    while True:
        try:
            jobs = claim_due_jobs()

            for job in jobs:
                process_job(job)

        except Exception:
            logger.exception("Worker polling failed.")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
    
