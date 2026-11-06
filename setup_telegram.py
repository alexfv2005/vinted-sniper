"""
One-time helper to wire up Telegram notifications.

Run it after you've created a bot with @BotFather and sent it a message.
It asks for your bot token, finds your chat id automatically, sends a test
message, and writes both into .env so the sniper can use them.

    python setup_telegram.py
"""

from __future__ import annotations

import sys

import requests


def get_chat_id(token: str) -> str | None:
    """Read the chat id from the most recent message sent to the bot."""
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
    r.raise_for_status()
    updates = r.json().get("result", [])
    if not updates:
        return None
    # take the chat id from the latest message
    for upd in reversed(updates):
        msg = upd.get("message") or upd.get("edited_message")
        if msg and "chat" in msg:
            return str(msg["chat"]["id"])
    return None


def send_test(token: str, chat_id: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": "✅ Vinted Sniper is connected."},
        timeout=10,
    )
    return r.ok


def write_env(token: str, chat_id: str) -> None:
    lines = [
        "# Written by setup_telegram.py\n",
        f"TELEGRAM_BOT_TOKEN={token}\n",
        f"TELEGRAM_CHAT_ID={chat_id}\n",
    ]
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(lines)


def main() -> int:
    print("Telegram setup for Vinted Sniper\n")
    print("First, if you haven't yet:")
    print("  1. Open Telegram, message @BotFather, send /newbot, follow the steps.")
    print("  2. Copy the bot token it gives you.")
    print("  3. Open a chat with your new bot and send it any message (e.g. 'hi').\n")

    token = input("Paste your bot token: ").strip()
    if not token or ":" not in token:
        print("That doesn't look like a bot token. Aborting.")
        return 1

    print("\nLooking for your chat id...")
    try:
        chat_id = get_chat_id(token)
    except requests.RequestException as e:
        print(f"Couldn't reach Telegram: {e}")
        return 1

    if not chat_id:
        print("No messages found. Send your bot a message first, then re-run this.")
        return 1

    print(f"Found chat id: {chat_id}")
    print("Sending a test message...")
    if send_test(token, chat_id):
        print("Test message sent, check your Telegram.")
    else:
        print("Chat id found but the test message failed. Writing .env anyway.")

    write_env(token, chat_id)
    print("\nSaved to .env. Run the sniper and hits go to Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
