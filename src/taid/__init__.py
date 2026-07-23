"""Telegram assistant userbot."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("taid")
except PackageNotFoundError:  # source running without installation
    __version__ = "0.0.0"

__all__ = ["__version__"]
