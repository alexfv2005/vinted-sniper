"""Tests for the parsing helpers in vinted_client.

These run without a browser: they only check how raw card data gets turned
into Listing objects, which is the fiddly, break-prone part.
"""

from vinted_sniper.vinted_client import _clean_title, _parse_price, _to_listing


def test_parse_price_simple():
    assert _parse_price("7,00 €") == 7.0
    assert _parse_price("18,00 €") == 18.0


def test_parse_price_thousands():
    assert _parse_price("1.234,50 €") == 1234.5
    assert _parse_price("1 234,50 €") == 1234.5


def test_parse_price_nbsp_and_prefix():
    assert _parse_price("28,00\xa0€") == 28.0
    assert _parse_price("€ 5,00") == 5.0


def test_parse_price_garbage_is_zero():
    assert _parse_price("") == 0.0
    assert _parse_price("kostenlos") == 0.0


def test_clean_title_strips_metadata():
    raw = "Damen Nike Jogginghose, Marke: Nike, Zustand: Sehr gut, Größe: S, 7.00 €, 8.05 €"
    assert _clean_title(raw) == "Damen Nike Jogginghose"


def test_clean_title_without_metadata():
    assert _clean_title("Just a title") == "Just a title"


def test_to_listing_full():
    raw = {
        "id": "10677354346",
        "href": "/items/10677354346-damen-nike-jogginghose",
        "title": "Damen Nike Jogginghose, Marke: Nike, Zustand: Sehr gut, Größe: S, 7.00 €, 8.05 €",
        "priceText": "7,00 €",
        "brand": "Nike",
        "subtitle": "S · Sehr gut",
        "photo": "https://images1.vinted.net/foo.jpg",
    }
    item = _to_listing(raw, "https://www.vinted.de")
    assert item.id == 10677354346
    assert item.title == "Damen Nike Jogginghose"
    assert item.price == 7.0
    assert item.brand == "Nike"
    assert item.size == "S"
    assert item.url == "https://www.vinted.de/items/10677354346-damen-nike-jogginghose"


def test_to_listing_size_from_subtitle():
    raw = {
        "id": "1", "href": "/items/1-x", "title": "X", "priceText": "5,00 €",
        "brand": "Nike", "subtitle": "M · Neu", "photo": None,
    }
    assert _to_listing(raw, "https://www.vinted.de").size == "M"
