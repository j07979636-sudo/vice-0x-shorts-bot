
"""VICE_0X Auto Shorts Bot: cost and safety guard.

Tracks daily usage in SQLite.
Enforces daily limits and storage protection.
Usage resets at midnight UTC.
"""

import shutil
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


class LimitExceeded(Exception):
    """Raised when an action exceeds a configured limit."""


_lock = threading.Lock()


def _daily_limits() -> dict:
    return {
        "uploads": (
            "Video uploads today",
            settings.max_uploads_per_day,
        ),
        "ai_calls": (
            "AI calls today",
            settings.max_ai_calls_per_day,
        ),
        "youtube_uploads": (
            "YouTube publishes today",
            settings.max_yt_uploads_per_day,
        ),
    }


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _validate_amount(amount: int) -> None:
    if (
        not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount <= 0
    ):
        raise ValueError("Amount must be a positive integer")


def _connect() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        settings.data_dir / "usage.db",
        timeout=10,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage (
            day TEXT NOT NULL,
            key TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (day, key)
        )
        """
    )

    return conn


def get_count(key: str) -> int:
    if key not in _daily_limits():
        raise ValueError(f"Unknown limit key: {key}")

    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT count FROM usage WHERE day = ? AND key = ?",
            (_today(), key),
        ).fetchone()

    return row[0] if row else 0


def consume(key: str, amount: int = 1) -> int:
    """Consume today's allowance or raise LimitExceeded."""

    _validate_amount(amount)

    limits = _daily_limits()

    if key not in limits:
        raise ValueError(f"Unknown limit key: {key}")

    label, maximum = limits[key]

    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT count FROM usage WHERE day = ? AND key = ?",
            (_today(), key),
        ).fetchone()

        current = row[0] if row else 0

        if current + amount > maximum:
            raise LimitExceeded(
                f"Daily limit reached: {label} "
                f"({current}/{maximum}). "
                "It resets at midnight UTC."
            )

        conn.execute(
            """
            INSERT INTO usage (day, key, count)
            VALUES (?, ?, ?)
            ON CONFLICT(day, key)
            DO UPDATE SET count = count + excluded.count
            """,
            (_today(), key, amount),
        )

        return current + amount


def refund(key: str, amount: int = 1) -> None:
    """Refund allowance when an operation fails."""

    _validate_amount(amount)

    if key not in _daily_limits():
        raise ValueError(f"Unknown limit key: {key}")

    with _lock, _connect() as conn:
        conn.execute(
            """
            UPDATE usage
            SET count = MAX(0, count - ?)
            WHERE day = ? AND key = ?
            """,
            (amount, _today(), key),
        )


def storage_used_bytes() -> int:
    """Calculate total uploaded file storage."""

    folder = settings.uploads_dir

    if not folder.exists():
        return 0

    return sum(
        path.stat().st_size
        for path in folder.rglob("*")
        if path.is_file()
    )


def storage_room_bytes() -> int:
    """Return remaining storage capacity."""

    cap = settings.max_storage_mb * 1024 * 1024

    return max(
        0,
        cap - storage_used_bytes(),
    )


def probe_duration_seconds(path: Path):
    """Read video duration using ffprobe.

    Returns None if ffprobe is unavailable.
    """

    ffprobe = shutil.which("ffprobe")

    if not ffprobe:
        return None

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        duration = float(result.stdout.strip())

        if duration <= 0:
            raise ValueError("Invalid video duration")

        return duration

    except (
        ValueError,
        subprocess.TimeoutExpired,
        OSError,
        subprocess.CalledProcessError,
    ):
        raise LimitExceeded(
            "That file is not a readable video."
        ) from None


def usage_snapshot() -> list:
    """Return usage information for the dashboard."""

    rows = []

    for key, (label, maximum) in _daily_limits().items():
        rows.append(
            {
                "label": label,
                "used": get_count(key),
                "limit": maximum,
            }
        )

    used_mb = round(
        storage_used_bytes() / (1024 * 1024),
        1,
    )

    rows.append(
        {
            "label": "Storage used (MB)",
            "used": used_mb,
            "limit": settings.max_storage_mb,
        }
    )

    return rows
    
