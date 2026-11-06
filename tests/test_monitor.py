"""Tests for the monitor's dedup + prime behavior, using a fake client."""

from vinted_sniper.filters import SearchFilter
from vinted_sniper.monitor import Monitor
from vinted_sniper.vinted_client import Listing


class FakeClient:
    """Returns whatever listings we queue up, ignoring query params."""

    def __init__(self):
        self.listings = []

    def search(self, *args, **kwargs):
        return list(self.listings)


class RecordingNotifier:
    def __init__(self):
        self.sent = []

    def notify(self, listing):
        self.sent.append(listing)


def make_listing(id_):
    return Listing(
        id=id_,
        title="Jacke",
        price=30.0,
        currency="EUR",
        brand="Carhartt",
        size="M",
        url=f"https://www.vinted.de/items/{id_}",
        photo_url=None,
    )


def test_prime_does_not_notify():
    client = FakeClient()
    client.listings = [make_listing(1), make_listing(2)]
    notifier = RecordingNotifier()
    mon = Monitor(client, notifier, [SearchFilter("jacke")])

    mon._prime()
    assert notifier.sent == []  # priming is silent


def test_new_listing_fires_once():
    client = FakeClient()
    notifier = RecordingNotifier()
    mon = Monitor(client, notifier, [SearchFilter("jacke")])

    mon._prime()  # starts empty
    client.listings = [make_listing(1)]

    mon._tick()
    mon._tick()  # second tick must not re-notify the same item

    assert len(notifier.sent) == 1
    assert notifier.sent[0].id == 1


def test_filter_blocks_notification():
    client = FakeClient()
    notifier = RecordingNotifier()
    # max_price below the listing's 30€, so it should never notify
    mon = Monitor(client, notifier, [SearchFilter("jacke", max_price=10)])

    mon._prime()
    client.listings = [make_listing(1)]
    mon._tick()

    assert notifier.sent == []
