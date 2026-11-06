"""Sends hits to Telegram, or just prints them if .env has no token/chat id."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

TG_URL = "https://api.telegram.org/bot{}/sendMessage"


def _esc(s):
    # telegram HTML mode only chokes on these three
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Notifier:
    def __init__(self, bot_token, chat_id, timeout=10.0):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.enabled = bool(bot_token and chat_id)
        if not self.enabled:
            log.warning("Telegram not configured, notifications will print to stdout")

    def notify(self, listing):
        msg = self._format(listing)
        if not self.enabled:
            print(msg)
            return
        try:
            r = requests.post(
                TG_URL.format(self.bot_token),
                data={
                    "chat_id": self.chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,  # keep the link preview under the message
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            # don't kill the loop over one failed message
            log.error("Telegram send failed: %s", e)

    @staticmethod
    def _format(l):
        lines = [f"<b>{_esc(l.title)}</b>", f"💶 {l.price:.2f} {l.currency}"]
        if l.brand:
            lines.append(f"🏷️ {_esc(l.brand)}")
        if l.size:
            lines.append(f"📏 {_esc(l.size)}")
        lines.append(f'\n<a href="{l.url}">Zum Angebot</a>')
        return "\n".join(lines)
