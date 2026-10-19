from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from taid.errors import SnapshotError

if TYPE_CHECKING:
    import logging
    from collections.abc import Awaitable, Callable

    from telethon.events import NewMessage

    from taid.models import MessageSnapshot
    from taid.ports import TelegramPort


def with_snapshot(
    telegram: TelegramPort, logger: logging.Logger, feature: str
) -> Callable[
    [Callable[[MessageSnapshot], Awaitable[None]]],
    Callable[[NewMessage.Event], Awaitable[None]],
]:
    def decorate(
        callback: Callable[[MessageSnapshot], Awaitable[None]],
    ) -> Callable[[NewMessage.Event], Awaitable[None]]:
        @wraps(callback)
        async def wrapped(event: NewMessage.Event) -> None:
            try:
                snapshot = telegram.snapshot(event)
            except SnapshotError:
                logger.warning(
                    "%s: %s skipped malformed event %s in chat %s",
                    feature,
                    callback.__name__,
                    event.id,
                    event.chat_id,
                    exc_info=True,
                )
                return

            await callback(snapshot)

        return wrapped

    return decorate
