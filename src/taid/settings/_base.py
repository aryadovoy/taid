from typing import Self

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    @classmethod
    def load(cls) -> Self:
        return cls()
