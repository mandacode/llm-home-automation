#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN in .env")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.load(response)

    if not payload.get("ok"):
        print(f"Telegram rejected the request: {payload}")
        return 1

    seen: dict[int, str] = {}
    for update in payload.get("result", []):
        message = update.get("message") or update.get("edited_message") or {}
        user = message.get("from")
        if user:
            name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
            seen[user["id"]] = f"{name} (@{user.get('username', 'none')})"

    if not seen:
        print("No messages found. Send anything to the bot and run again.")
        print("Telegram keeps unfetched updates for 24h only.")
        return 0

    print("Users found:\n")
    for user_id, label in seen.items():
        print(f"  {user_id}  —  {label}")
    print("\nAdd to .env:")
    print(f"  TELEGRAM_ALLOWED_USER_IDS={','.join(str(i) for i in seen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
