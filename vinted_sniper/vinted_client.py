"""
Reads Vinted search results by driving a headless Chromium (Playwright).

Vinted sits behind Cloudflare and renders its search results server-side, so
there's no plain JSON endpoint to hit anymore. A bare requests call just gets
a 404/bot-block. Chromium loads the search page like any visitor would (which
clears the Cloudflare check on its own) and we read the item cards out of the
rendered page.

Slower than a raw HTTP call, but it gets through. Read-only: same listings a
logged-out visitor sees.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass


log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.vinted.de"


@dataclass(frozen=True)
class Listing:
    id: int
    title: str
    price: float
    currency: str
    brand: str
    size: str
    url: str
    photo_url: str | None


# the item cards are rendered client-side, so pull them out in the page itself.
# each grid-item carries the id in its href and the rest in testid'd children.
_EXTRACT_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('[data-testid="grid-item"]').forEach(card => {
    const link = card.querySelector('a[href*="/items/"]');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    const m = href.match(/\/items\/(\d+)/);
    if (!m) return;
    const price = card.querySelector('[data-testid$="--price-text"]');
    const brand = card.querySelector('[data-testid$="--description-title"]');
    const sub = card.querySelector('[data-testid$="--description-subtitle"]');
    const img = card.querySelector('img');
    out.push({
      id: m[1],
      href: href.split('?')[0],
      title: link.getAttribute('title') || '',
      priceText: price ? price.textContent.trim() : '',
      brand: brand ? brand.textContent.trim() : '',
      subtitle: sub ? sub.textContent.trim() : '',  // e.g. "S · Sehr gut"
      photo: img ? img.getAttribute('src') : null,
    });
  });
  return out;
}
"""


def _parse_price(text: str) -> float:
    # german formatting: "7,00 €", "1.234,50 €", "1 234,50 €" -> float
    t = text.replace("\xa0", "").replace(" ", "").replace("€", "").strip()
    # strip thousands separators (dots), then turn the decimal comma into a dot
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    m = re.search(r"\d+(\.\d+)?", t)
    return float(m.group()) if m else 0.0


def _clean_title(title_attr: str) -> str:
    # the title attr is "Real Title, Marke: .., Zustand: .., Größe: .., 7.00 €, 8.05 €"
    # everything up to the first ", Marke:" is the actual listing title.
    return title_attr.split(", Marke:")[0].strip()


def _to_listing(raw: dict, base_url: str) -> Listing:
    # subtitle looks like "S · Sehr gut" -> size is the part before the dot
    size = raw["subtitle"].split("·")[0].strip() if raw["subtitle"] else ""
    return Listing(
        id=int(raw["id"]),
        title=_clean_title(raw["title"]) or raw["brand"],
        price=_parse_price(raw["priceText"]),
        currency="EUR",
        brand=raw["brand"],
        size=size,
        url=base_url + raw["href"],
        photo_url=raw["photo"],
    )


class VintedClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0, headless: bool = True):
        self.base_url = base_url.rstrip("/")
        self.timeout_ms = int(timeout * 1000)
        self.headless = headless
        self._pw = None
        self._browser = None
        self._page = None

    def _ensure_browser(self):
        # start the browser lazily and keep it alive across polls, so we pay the
        # cloudflare/cookie cost once instead of on every search.
        if self._page is not None:
            return
        # imported here so the rest of the package works without playwright
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
        )

    def search(self, search_text: str = "", *, price_from=None, price_to=None,
               order: str = "newest_first", **_ignored) -> list[Listing]:
        """Load the catalog search page and read the rendered item cards."""
        self._ensure_browser()

        params = {"search_text": search_text, "order": order}
        if price_from is not None:
            params["price_from"] = price_from
        if price_to is not None:
            params["price_to"] = price_to
        url = f"{self.base_url}/catalog?{urllib.parse.urlencode(params)}"

        self._page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
        # wait for at least one item card to render (cloudflare + hydration)
        try:
            self._page.wait_for_selector('[data-testid="grid-item"]', timeout=self.timeout_ms)
        except Exception:
            log.warning("No items rendered for '%s' (page may be blocked or empty)", search_text)
            return []

        raw_items = self._page.evaluate(_EXTRACT_JS)
        return [_to_listing(r, self.base_url) for r in raw_items]

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = self._browser = self._pw = None
