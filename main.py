"""Vinted sniper: polls Vinted searches and pings me when something new shows up.

Two ways to run it:

  1. Quick, straight from the command line:
       python main.py "carhartt jacke" --max-price 50 --sizes M L
     (or just: ./run.sh "carhartt jacke" 50)

  2. Many searches at once from a file:
       python main.py --config config.yaml

Notifications go to Telegram if .env has a token + chat id, otherwise they
just print to the terminal, which is fine for trying it out.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import yaml
from dotenv import load_dotenv

from vinted_sniper import Monitor, Notifier, SearchFilter, VintedClient

log = logging.getLogger("sniper")

# below this vinted starts rate-limiting
MIN_POLL = 30
DEFAULT_POLL = 60
DEFAULT_BASE = "https://www.vinted.de"


def read_cfg(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        # usually a tab or a missing space after a colon somewhere
        log.error("can't parse %s: %s", path, e)
        return None


def to_filter(i, raw):
    if not raw or not raw.get("search_text"):
        log.error("filter #%d has no search_text, skipping it", i + 1)
        return None
    return SearchFilter(
        search_text=raw["search_text"],
        max_price=raw.get("max_price"),
        min_price=raw.get("min_price"),  # mostly there to skip the 1€ scam listings
        sizes=raw.get("sizes", []),
        brands=raw.get("brands", []),
        keywords=raw.get("keywords", []),
    )


def from_config(path):
    """Build filters + settings from a yaml file. Returns (filters, poll, base)."""
    if not os.path.exists(path):
        log.error("No config file at %s. Copy config.example.yaml first.", path)
        return None
    cfg = read_cfg(path)
    if cfg is None:
        return None

    filters = [to_filter(i, raw) for i, raw in enumerate(cfg.get("filters") or [])]
    filters = [f for f in filters if f]
    if not filters:
        log.error("No usable filters in %s.", path)
        return None

    s = cfg.get("settings") or {}
    return filters, s.get("poll_interval", DEFAULT_POLL), s.get("base_url", DEFAULT_BASE)


def from_args(a):
    """Build a single filter straight from the command line args."""
    flt = SearchFilter(
        search_text=a.query,
        max_price=a.max_price,
        min_price=a.min_price,
        sizes=a.sizes or [],
        brands=a.brands or [],
        keywords=a.keywords or [],
    )
    return [flt], a.poll, a.base_url


def build_parser():
    p = argparse.ArgumentParser(
        description="Watch Vinted and get pinged when a matching item is listed.",
    )
    p.add_argument("query", nargs="?", help='what to search for, e.g. "carhartt jacke"')
    p.add_argument("--config", help="yaml file with multiple searches instead of a single query")
    p.add_argument("--max-price", type=float, dest="max_price", help="ignore anything pricier")
    p.add_argument("--min-price", type=float, dest="min_price", help="ignore suspiciously cheap listings")
    p.add_argument("--sizes", nargs="+", help="only these sizes, e.g. --sizes M L")
    p.add_argument("--brands", nargs="+", help="only these brands")
    p.add_argument("--keywords", nargs="+", help="title must contain all of these")
    p.add_argument("--poll", type=int, default=DEFAULT_POLL, help=f"seconds between checks (default {DEFAULT_POLL})")
    p.add_argument("--base-url", default=DEFAULT_BASE, dest="base_url", help="e.g. https://www.vinted.fr for France")
    return p


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    load_dotenv()

    args = build_parser().parse_args()

    # config file wins if given, otherwise fall back to the plain query
    if args.config:
        result = from_config(args.config)
    elif args.query:
        result = from_args(args)
    else:
        log.error('Give me something to search for, e.g. python main.py "carhartt jacke" --max-price 50')
        return 1

    if result is None:
        return 1
    filters, poll, base = result

    if poll < MIN_POLL:
        log.warning("poll interval %ss is too low, using %ss", poll, MIN_POLL)
        poll = MIN_POLL

    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")

    log.info("watching %d search(es), every %ss", len(filters), poll)
    Monitor(
        client=VintedClient(base_url=base),
        notifier=Notifier(bot_token=token, chat_id=chat),
        filters=filters,
        poll_interval=poll,
    ).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
