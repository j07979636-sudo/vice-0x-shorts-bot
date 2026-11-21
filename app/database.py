"""VICE_0X database module.

Stores daily automation usage counters in SQLite.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def get_connection():
    """Create a connection to the application database."""
    db_path = Path(settings.data_dir) / "vice0x.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create required database tables."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                day TEXT PRIMARY KEY,
                videos_processed INTEGER DEFAULT 0,
                uploads_completed INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0
            )
        """)
        connection.commit()


def get_today():
    """Return the current UTC date."""
    return datetime.now(timezone.utc).date().isoformat()


def get_daily_usage():
    """Get today's usage counters."""
    initialize_database()

    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO daily_usage (day) VALUES (?)",
            (get_today(),),
        )
        row = connection.execute(
            "SELECT * FROM daily_usage WHERE day = ?",
            (get_today(),),
        ).fetchone()

        return dict(row)


def increment_usage(counter, amount=1):
    """Increment a supported daily usage counter."""
    allowed = {
        "videos_processed",
        "uploads_completed",
        "api_calls",
    }

    if counter not in allowed:
        raise ValueError("Unsupported usage counter")

    if not isinstance(amount, int) or amount < 0:
        raise ValueError("Amount must be a non-negative integer")

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            f"UPDATE daily_usage SET {counter} = {counter} + ? WHERE day = ?",
            (amount, get_today()),
        )
        connection.commit()
        
