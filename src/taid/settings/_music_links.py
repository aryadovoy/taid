from pydantic import Field

from ._base import BaseConfig


class MusicLinkConfig(BaseConfig):
    model_config = BaseConfig.model_config | {"env_prefix": "MUSIC_LINKS_"}

    enabled: bool = True
    bot_username: str = "odesli_bot"
    domains: tuple[str, ...] = ("open.spotify.com", "music.yandex.ru")
    timeout_seconds: int = Field(default=45, ge=5, le=300)
    error_chat: str = "me"
