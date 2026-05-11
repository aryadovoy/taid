from __future__ import annotations

from taid.settings import MergeConfig, MusicLinkConfig


def test_default_merge_settings() -> None:
    settings = MergeConfig()

    assert settings.enabled is True
    assert settings.timeout_seconds == 30
    assert settings.break_prefix == ". "


def test_default_music_domains_are_limited() -> None:
    settings = MusicLinkConfig()

    assert settings.domains == ("open.spotify.com", "music.yandex.ru")
    assert settings.bot_username == "odesli_bot"
    assert settings.error_chat == "me"
