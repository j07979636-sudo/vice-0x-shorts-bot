"""VICE_0X Auto Shorts Bot: cost and safety guard.

Daily counters are stored in a small SQLite file. When a limit is reached the
app stops the action and says why. It never keeps going.
Days roll over at midnight UTC.
"""

import shutil
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


class LimitExceeded(Exception):
    """Raised when an action would break a configured limit."""


_lock = threading.Lock()


def _daily_limits() -> dict:
    return {
        "uploads": ("Video uploads today", settings.max_uploads_per_day),
        "ai_calls": ("AI calls today", settings.max_ai_calls_per_day),
        "youtube_uploads": ("YouTube publishes today", settings.max_yt_uploads_per_day),
    }


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _connect() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.data_dir / "usage.db", timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS usage ("
        "day TEXT NOT NULL, key TEXT NOT NULL, count INTEGER NOT NULL, "
        "PRIMARY KEY (day, key))"
    )
    return conn


def get_count(key: str) -> int:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT count FROM usage WHERE day = ? AND key = ?", (_today(), key)
        ).fetchone()
    return row[0] if row else 0


def consume(key: str, amount: int = 1) -> int:
    """Use up `amount` of today's allowance for `key`. Raises LimitExceeded if over."""
    limits = _daily_limits()
    if key not in limits:
        raise ValueError(f"Unknown limit key: {key}")
    label, maximum = limits[key]
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT count FROM usage WHERE day = ? AND key = ?", (_today(), key)
        ).fetchone()
        current = row[0] if row else 0
        if current + amount > maximum:
            raise LimitExceeded(
                f"Daily limit reached: {label} ({current}/{maximum}). "
                "It resets at midnight UTC."
            )
        conn.execute(
            "INSERT INTO usage (day, key, count) VALUES (?, ?, ?) "
            "ON CONFLICT(day, key) DO UPDATE SET count = count + excluded.count",
            (_today(), key, amount),
        )
        return current + amount


def refund(key: str, amount: int = 1) -> None:
    """Give back allowance when an action failed before doing real work."""
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE usage SET count = MAX(0, count - ?) WHERE day = ? AND key = ?",
            (amount, _today(), key),
        )


def storage_used_bytes() -> int:
    folder = settings.uploads_dir
    if not folder.exists():
        return 0
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def storage_room_bytes() -> int:
    """Bytes still available before the storage cap is hit."""
    cap = settings.max_storage_mb * 1024 * 1024
    return max(0, cap - storage_used_bytes())


def probe_duration_seconds(path: Path):
    """Return video length in seconds using ffprobe.

    Returns None when ffprobe is not installed (the length check is skipped).
    Raises LimitExceeded when ffprobe is installed but cannot read the file.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, OSError):
        raise LimitExceeded("That file is not a readable video.")


def usage_snapshot() -> list:
    """Numbers shown on the dashboard."""
    rows = []
    for key, (label, maximum) in _daily_limits().items():
        rows.append({"label": label, "used": get_count(key), "limit": maximum})
    used_mb = round(storage_used_bytes() / (1024 * 1024), 1)
    rows.append({"label": "Storage used (MB)", "used": used_mb, "limit": settings.max_storage_mb})
    return rows
