
"""VICE_0X background worker.

Claims due jobs safely and validates their input files.
Actual video processing and YouTube uploading are separate stages.
"""

import logging
import os
import socket
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database import get_connection, initialize_database

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
JOB_TIMEOUT_MINUTES = 30
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


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
                created_at TEXT NOT NULL,
                claimed_at TEXT,
                worker_id TEXT,
                error_message TEXT
            )
        """)

        # Add columns safely for databases created by older versions.
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
        }

        for name, definition in migrations.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE scheduled_jobs ADD COLUMN {name} {definition}"
                )

        connection.commit()


def add_job(video_path: str, scheduled_time: str) -> int:
    """Save a future schedule to the database."""

    if not isinstance(video_path, str) or not video_path.strip():
        raise ValueError("A valid video path is required.")

    if not isinstance(scheduled_time, str) or not scheduled_time.strip():
        raise ValueError("A scheduled time is required.")

    scheduled_text = scheduled_time.strip()

    try:
        scheduled = datetime.fromisoformat(
            scheduled_text.replace("Z", "+00:00")
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
                video_path.strip(),
                scheduled.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_due_jobs() -> list[dict]:
    """Return currently pending jobs that are due."""

    initialize_jobs_table()
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM scheduled_jobs
            WHERE status = 'pending'
              AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            """,
            (now,),
        ).fetchall()

    return [dict(row) for row in rows]


def claim_due_jobs(limit: int = 5) -> list[dict]:
    """Atomically claim due jobs so multiple workers do not claim the same job."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Job limit must be a positive integer.")

    initialize_jobs_table()
    now = datetime.now(timezone.utc).isoformat()
    claimed = []

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        rows = connection.execute(
            """
            SELECT id FROM scheduled_jobs
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
                    worker_id = ?
                WHERE id = ? AND status = 'pending'
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
) -> None:
    """Update a job status and clear its worker claim when finished."""

    allowed = {"pending", "processing", "completed", "failed"}

    if status not in allowed:
        raise ValueError("Unsupported job status.")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE scheduled_jobs
            SET status = ?,
                error_message = ?,
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
                status,
                status,
                job_id,
            ),
        )
        connection.commit()


def recover_stale_jobs():
    """Return jobs abandoned by a worker to pending status."""

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


def process_job(job: dict) -> None:
    """Validate a claimed job without uploading it yet."""

    job_id = job["id"]
    path = Path(job["video_path"])

    try:
        if not path.is_file():
            raise FileNotFoundError(
                f"Scheduled video no longer exists: {path}"
            )

        logger.info(
            "Job %s is ready for the video-processing stage.",
            job_id,
        )

        # Actual editing and YouTube publishing will be connected
        # after the processing pipeline is tested.
        mark_job_status(job_id, "pending")

    except Exception as exc:
        logger.exception("Job %s failed validation.", job_id)
        mark_job_status(job_id, "failed", str(exc))


def run_worker():
    """Continuously claim and validate due jobs."""

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
            
