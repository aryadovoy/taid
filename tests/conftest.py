from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from taid.models import ChatRef, MessageRef, MessageSnapshot
from taid.sent_registry import SentMessageRegistry

if TYPE_CHECKING:
    from datetime import datetime

    from telethon.events import NewMessage


@dataclass
class FakeMessage:
    text: str | None
    out: bool = True
    media: object | None = None
    forward: object | None = None
    reply_to_msg_id: int | None = None
    topic_id: int | None = None
    buttons: object | None = None
    grouped_id: int | None = None
    date: datetime | None = None


@dataclass
class FakeEvent:
    chat_id: int
    message_id: int
    message: FakeMessage

    @property
    def id(self) -> int:
        return self.message_id


@dataclass
class FakeTelegramPort:
    edits: list[tuple[MessageRef, str]] = field(default_factory=list)
    deletes: list[MessageRef] = field(default_factory=list)
    sends: list[tuple[ChatRef, str, int | None]] = field(default_factory=list)
    sent_refs: list[MessageRef] = field(default_factory=list)
    sent_registry: SentMessageRegistry = field(default_factory=SentMessageRegistry)
    _next_id: int = field(default=10_000, init=False)

    def snapshot(self, event: NewMessage.Event) -> MessageSnapshot:
        message = event.message
        chat_id = event.chat_id
        if chat_id is None:
            raise ValueError("event has no chat_id")
        return MessageSnapshot(
            ref=MessageRef(chat_id=chat_id, message_id=event.id),
            text=message.text,
            outgoing=message.out,
            has_media=message.media is not None,
            is_forward=message.forward is not None,
            replied_message_id=message.reply_to_msg_id,
            topic_id=message.topic_id,
            has_buttons=message.buttons is not None,
            grouped_id=message.grouped_id,
            date=message.date,
        )

    async def edit_message(self, ref: MessageRef, text: str) -> None:
        self.edits.append((ref, text))

    async def delete_message(self, ref: MessageRef) -> None:
        self.deletes.append(ref)

    async def send_message(
        self, chat: ChatRef, text: str, *, reply_to: int | None = None
    ) -> MessageRef:
        self.sends.append((chat, text, reply_to))
        self._next_id += 1
        chat_id = chat if isinstance(chat, int) else 0
        ref = MessageRef(chat_id=chat_id, message_id=self._next_id)
        self.sent_refs.append(ref)
        self.sent_registry.add(ref)
        return ref


def make_snapshot(  # noqa: PLR0913
    text: str,
    *,
    chat_id: int = 1,
    message_id: int = 1,
    outgoing: bool = True,
    has_media: bool = False,
    replied_message_id: int | None = None,
    topic_id: int | None = None,
    date: datetime | None = None,
) -> MessageSnapshot:
    return MessageSnapshot(
        ref=MessageRef(chat_id=chat_id, message_id=message_id),
        text=text,
        outgoing=outgoing,
        has_media=has_media,
        replied_message_id=replied_message_id,
        topic_id=topic_id,
        date=date,
    )
