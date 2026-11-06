"""Tests for SearchFilter.matches(), where the actual match decisions happen."""

from vinted_sniper.filters import SearchFilter
from vinted_sniper.vinted_client import Listing


def make_listing(**overrides):
    base = dict(
        id=1,
        title="Carhartt WIP Jacke",
        price=45.0,
        currency="EUR",
        brand="Carhartt WIP",
        size="M",
        url="https://www.vinted.de/items/1",
        photo_url=None,
    )
    base.update(overrides)
    return Listing(**base)


def test_price_ceiling_rejects_expensive():
    flt = SearchFilter(search_text="jacke", max_price=40)
    assert not flt.matches(make_listing(price=45.0))


def test_price_ceiling_accepts_cheap():
    flt = SearchFilter(search_text="jacke", max_price=50)
    assert flt.matches(make_listing(price=45.0))


def test_price_floor_rejects_scam():
    flt = SearchFilter(search_text="jacke", min_price=10)
    assert not flt.matches(make_listing(price=1.0))


def test_size_filter_is_case_insensitive():
    flt = SearchFilter(search_text="jacke", sizes=["m", "l"])
    assert flt.matches(make_listing(size="M"))


def test_size_filter_rejects_wrong_size():
    flt = SearchFilter(search_text="jacke", sizes=["XL"])
    assert not flt.matches(make_listing(size="M"))


def test_brand_filter():
    flt = SearchFilter(search_text="jacke", brands=["Carhartt WIP"])
    assert flt.matches(make_listing(brand="Carhartt WIP"))
    assert not flt.matches(make_listing(brand="Nike"))


def test_keywords_all_required():
    flt = SearchFilter(search_text="jacke", keywords=["carhartt", "jacke"])
    assert flt.matches(make_listing(title="Carhartt WIP Jacke"))
    assert not flt.matches(make_listing(title="Carhartt Hose"))


def test_empty_filter_matches_everything():
    flt = SearchFilter(search_text="anything")
    assert flt.matches(make_listing())
