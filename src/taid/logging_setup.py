import logging
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_RESET = "\033[0m"
_DIM = "\033[2m"
_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return (
            f"{_DIM}{timestamp}{_RESET} "
            f"{color}{record.levelname:<8}{_RESET} "
            f"{_DIM}{record.name}{_RESET} "
            f"{message}"
        )


def configure_logging(level: LogLevel) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)

    if level != "DEBUG":
        logging.getLogger("telethon").setLevel("WARNING")
