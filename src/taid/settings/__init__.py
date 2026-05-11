from pydantic import Field

from ._app import AppConfig
from ._base import BaseConfig
from ._merge import MergeConfig
from ._music_links import MusicLinkConfig
from ._telegram import TelegramConfig


class Config(BaseConfig):
    app: AppConfig = Field(default_factory=AppConfig.load)
    merge: MergeConfig = Field(default_factory=MergeConfig.load)
    music_links: MusicLinkConfig = Field(default_factory=MusicLinkConfig.load)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig.load)


__all__ = [
    "AppConfig",
    "BaseConfig",
    "Config",
    "MergeConfig",
    "MusicLinkConfig",
    "TelegramConfig",
]
