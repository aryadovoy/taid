from pathlib import Path

from pydantic import Field, SecretStr

from ._base import BaseConfig


class TelegramConfig(BaseConfig):
    model_config = BaseConfig.model_config | {"env_prefix": "TELEGRAM_"}

    api_id: int = Field(gt=0)
    api_hash: SecretStr
    session_path: Path = Path("./data/taid.session")
