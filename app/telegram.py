"""VICE_0X Telegram notification module."""

import os
import urllib.error
import urllib.parse
import urllib.request


class TelegramError(Exception):
    """Raised when Telegram notification fails."""


def send_message(message: str) -> bool:
    """Send a notification using a Telegram bot."""

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise TelegramError("Telegram credentials are missing.")

    if not message or not message.strip():
        raise ValueError("Message cannot be empty.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
    }).encode()

    request = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TelegramError("Telegram notification failed.") from exc
  
