"""What counts as a hit. One SearchFilter = one search from config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field

from .vinted_client import Listing


def _lower(xs):
    return {x.lower() for x in xs}


@dataclass
class SearchFilter:
    # search_text goes to vinted as the query, the rest is checked locally.
    # empty sizes/brands/keywords = don't care
    search_text: str
    max_price: float | None = None
    min_price: float | None = None  # for the 1€ scam listings
    sizes: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)  # ALL must be in the title

    def matches(self, item: Listing) -> bool:
        if self.max_price is not None and item.price > self.max_price:
            return False
        if self.min_price is not None and item.price < self.min_price:
            return False
        if self.sizes and item.size.lower() not in _lower(self.sizes):
            return False
        if self.brands and item.brand.lower() not in _lower(self.brands):
            return False

        title = item.title.lower()
        return all(kw.lower() in title for kw in self.keywords)
