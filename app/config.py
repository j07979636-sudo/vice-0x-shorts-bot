"""VICE_0X Auto Shorts Bot: configuration.

All settings come from environment variables (Hugging Face Secrets/Variables).
Nothing secret is ever written in source code.
Every limit also has a hard ceiling, so a typo in a secret cannot remove
your cost protection.
"""

import os
from dataclasses import dataclass
from pathlib import Path

BRAND_NAME = "VICE_0X"  # zero, not the letter O
APP_TITLE = f"{BRAND_NAME} Auto Shorts Bot"
REPO_NAME = "vice-0x-shorts-bot"


def _int_env(name: str, default: int, minimum: int, ceiling: int) -> int:
    """Read an integer env var, falling back to default and clamping to a safe range."""
    raw = os.environ.get(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(value, ceiling))


@dataclass(frozen=True)
class Settings:
    dashboard_user: str
    dashboard_password: str
    max_upload_mb: int
    max_video_minutes: int
    max_uploads_per_day: int
    max_ai_calls_per_day: int
    max_yt_uploads_per_day: int
    max_storage_mb: int
    data_dir: Path

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


def load_settings() -> Settings:
    return Settings(
        dashboard_user=os.environ.get("DASHBOARD_USER", "vice0x").strip() or "vice0x",
        dashboard_password=os.environ.get("DASHBOARD_PASSWORD", ""),
        max_upload_mb=_int_env("MAX_UPLOAD_MB", 200, 1, 500),
        max_video_minutes=_int_env("MAX_VIDEO_MINUTES", 30, 1, 120),
        max_uploads_per_day=_int_env("MAX_UPLOADS_PER_DAY", 5, 1, 50),
        max_ai_calls_per_day=_int_env("MAX_AI_CALLS_PER_DAY", 50, 1, 500),
        # YouTube's free quota allows roughly 6 uploads/day, so 6 is the ceiling.
        max_yt_uploads_per_day=_int_env("MAX_YT_UPLOADS_PER_DAY", 4, 1, 6),
        max_storage_mb=_int_env("MAX_STORAGE_MB", 2000, 100, 10000),
        data_dir=Path(os.environ.get("DATA_DIR", "/tmp/vice0x-data")),
    )


settings = load_settings()
