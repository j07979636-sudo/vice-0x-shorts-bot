
"""VICE_0X Telegram notification module."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class TelegramError(Exception):
    """Raised when Telegram notification fails."""


def send_message(message: str) -> bool:
    """Send a notification using a Telegram bot."""

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise TelegramError("Telegram credentials are missing.")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty.")

    if len(message) > 4096:
        raise ValueError("Telegram message exceeds 4096 characters.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message.strip(),
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))

            if response.status != 200 or not result.get("ok"):
                raise TelegramError("Telegram rejected the message.")

            return True

    except urllib.error.HTTPError as exc:
        raise TelegramError(
            f"Telegram API returned HTTP {exc.code}."
        ) from exc

    except (urllib.error.URLError, TimeoutError) as exc:
        raise TelegramError("Telegram connection failed.") from exc

    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TelegramError("Invalid Telegram API response.") from exc
        
