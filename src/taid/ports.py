from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from telethon.events import NewMessage
    from telethon.events.common import EventBuilder

    from taid.models import ChatRef, MessageRef, MessageSnapshot


class TelegramPort(Protocol):
    def snapshot(self, event: NewMessage.Event) -> MessageSnapshot: ...

    async def edit_message(self, ref: MessageRef, text: str) -> None: ...

    async def delete_message(self, ref: MessageRef) -> None: ...

    async def send_message(
        self, chat: ChatRef, text: str, *, reply_to: int | None = None
    ) -> MessageRef: ...


class TelegramClientPort(Protocol):
    def add_event_handler(
        self,
        callback: Callable[[NewMessage.Event], Awaitable[None]],
        event: EventBuilder,
    ) -> None: ...
