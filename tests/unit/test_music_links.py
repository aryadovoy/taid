from __future__ import annotations

import pytest

from taid.features.music_links import MusicLinkService
from taid.settings import MusicLinkConfig


def test_accepts_single_supported_url_with_surrounding_text() -> None:
    service = MusicLinkService(MusicLinkConfig())

    url = service.single_supported_url("listen to https://open.spotify.com/track/1 please")

    assert url == "https://open.spotify.com/track/1"


def test_ignores_unsupported_urls() -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert service.single_supported_url("https://example.com/x") is None


@pytest.mark.parametrize(
    "text",
    [
        "https://open.spotify.com/track/1 https://music.yandex.ru/album/2",
        "https://open.spotify.com/track/1 https://example.com/details",
        "https://open.spotify.com/track/1 https://open.spotify.com/track/1",
    ],
)
def test_ignores_messages_with_multiple_explicit_urls(text: str) -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert service.single_supported_url(text) is None


def test_ignores_hidden_link_without_explicit_url() -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert service.single_supported_url("listen to this track") is None


def test_strips_trailing_punctuation() -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert (
        service.single_supported_url("Listen: https://open.spotify.com/track/1!")
        == "https://open.spotify.com/track/1"
    )


def test_detects_supported_url_for_merge_exemption_in_multi_link_message() -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert service.has_supported_url("https://open.spotify.com/track/1 https://example.com/details")


def test_response_matches_request_by_replied_message() -> None:
    service = MusicLinkService(MusicLinkConfig())
    first = service.enqueue(chat=10, url="https://open.spotify.com/track/1", sent_message_id=100)
    second = service.enqueue(chat=20, url="https://music.yandex.ru/album/2", sent_message_id=200)

    assert service.match_response(200) == second
    assert service.match_response(100) == first
    assert service.match_response(100) is None


def test_response_to_unknown_message_is_dropped() -> None:
    service = MusicLinkService(MusicLinkConfig())
    service.enqueue(chat=10, url="https://open.spotify.com/track/1", sent_message_id=100)

    assert service.match_response(999) is None
    assert service.match_response(100) is not None


def test_response_without_reply_falls_back_to_oldest_request() -> None:
    service = MusicLinkService(MusicLinkConfig())
    first = service.enqueue(chat=10, url="https://open.spotify.com/track/1", sent_message_id=100)
    second = service.enqueue(chat=20, url="https://music.yandex.ru/album/2", sent_message_id=200)

    assert service.match_response(None) == first
    assert service.match_response(None) == second
    assert service.match_response(None) is None


def test_enqueue_stores_topic_id() -> None:
    service = MusicLinkService(MusicLinkConfig())

    request = service.enqueue(
        chat=10, url="https://open.spotify.com/track/1", sent_message_id=100, topic_id=7
    )

    assert request.original_topic_id == 7
    assert service.match_response(100) == request


def test_remove_drops_pending_request() -> None:
    service = MusicLinkService(MusicLinkConfig())
    request = service.enqueue(chat=10, url="https://open.spotify.com/track/1", sent_message_id=100)

    assert service.remove(request.request_id) == request
    assert service.match_response(100) is None


@pytest.mark.parametrize(
    "url", ["https://open.spotify.com/track/abc", "https://music.yandex.ru/album/1"]
)
def test_supports_configured_domains(url: str) -> None:
    service = MusicLinkService(MusicLinkConfig())

    assert service.single_supported_url(url) == url
