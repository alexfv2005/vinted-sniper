"""Poll loop. Remembers listing ids per filter so every item pings once."""

from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)


class Monitor:
    def __init__(self, client, notifier, filters, poll_interval=60.0):
        self.client = client
        self.notifier = notifier
        self.filters = filters
        self.poll_interval = poll_interval
        # filter index -> ids already seen (notified or not)
        self._seen = {i: set() for i in range(len(filters))}

    def _fetch(self, flt, what):
        try:
            return self.client.search(flt.search_text, price_from=flt.min_price, price_to=flt.max_price)
        except Exception as e:
            log.error("%s failed for '%s': %s", what, flt.search_text, e)
            return None

    def _prime(self):
        # first round is silent, otherwise you get the whole current catalog in telegram
        for i, flt in enumerate(self.filters):
            items = self._fetch(flt, "Prime")
            if items is None:
                continue
            self._seen[i].update(it.id for it in items)
            log.info("Primed '%s' with %d existing listings", flt.search_text, len(items))

    def _tick(self):
        for i, flt in enumerate(self.filters):
            for it in self._fetch(flt, "Poll") or []:
                if it.id in self._seen[i]:
                    continue
                # mark before matching, no point checking a reject again next round
                self._seen[i].add(it.id)
                if flt.matches(it):
                    log.info("HIT: %s (%.2f %s)", it.title, it.price, it.currency)
                    self.notifier.notify(it)

    def run(self):
        log.info("Priming %d filter(s)...", len(self.filters))
        self._prime()
        log.info("Watching. Polling every %.0fs. Ctrl+C to stop.", self.poll_interval)
        try:
            while True:
                self._tick()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            log.info("Stopped.")
        finally:
            # shut the browser down cleanly, otherwise chromium lingers
            close = getattr(self.client, "close", None)
            if close:
                close()
