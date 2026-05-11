from typing import Literal

from ._base import BaseConfig


class AppConfig(BaseConfig):
    model_config = BaseConfig.model_config | {"env_prefix": "APP_"}

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
