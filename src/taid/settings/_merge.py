from pydantic import Field

from ._base import BaseConfig


class MergeConfig(BaseConfig):
    model_config = BaseConfig.model_config | {"env_prefix": "MERGE_"}

    enabled: bool = True
    timeout_seconds: int = Field(default=30, ge=1, le=600)
    break_prefix: str = Field(default=". ", min_length=1)
