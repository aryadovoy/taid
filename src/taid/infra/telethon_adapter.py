from __future__ import annotations

from typing import TYPE_CHECKING

from telethon.utils import get_peer_id

from taid.models import ChatRef, MessageRef, MessageSnapshot

if TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events import NewMessage
    from telethon.tl.types import MessageReplyHeader

    from taid.sent_registry import SentMessageRegistry


def reply_context(reply_to: MessageReplyHeader | None) -> tuple[int | None, int | None]:
    if reply_to is None:
        return None, None
    top = reply_to.reply_to_top_id
    msg_id = reply_to.reply_to_msg_id
    if reply_to.forum_topic:
        topic_id = top if top is not None else msg_id
        replied_id = msg_id if msg_id is not None and msg_id != topic_id else None
        return topic_id, replied_id
    return top, msg_id


class TelethonAdapter:
    def __init__(self, client: TelegramClient, sent_registry: SentMessageRegistry) -> None:
        self._client = client
        self._sent_registry = sent_registry

    def snapshot(self, event: NewMessage.Event) -> MessageSnapshot:
        message = event.message
        chat_id = event.chat_id
        if chat_id is None:
            raise ValueError("event has no chat_id")
        topic_id, replied_id = reply_context(message.reply_to)
        return MessageSnapshot(
            ref=MessageRef(chat_id=chat_id, message_id=event.id),
            text=message.text,
            outgoing=message.out,
            has_media=message.media is not None,
            is_forward=message.forward is not None,
            replied_message_id=replied_id,
            topic_id=topic_id,
            has_buttons=message.buttons is not None,
            grouped_id=message.grouped_id,
            date=message.date,
        )

    async def edit_message(self, ref: MessageRef, text: str) -> None:
        await self._client.edit_message(ref.chat_id, ref.message_id, text, link_preview=False)

    async def delete_message(self, ref: MessageRef) -> None:
        await self._client.delete_messages(ref.chat_id, [ref.message_id])

    async def send_message(
        self, chat: ChatRef, text: str, *, reply_to: int | None = None
    ) -> MessageRef:
        if reply_to is None:
            msg = await self._client.send_message(chat, text, link_preview=False)
        else:
            msg = await self._client.send_message(chat, text, link_preview=False, reply_to=reply_to)
        ref = MessageRef(chat_id=get_peer_id(msg.peer_id), message_id=msg.id)
        self._sent_registry.add(ref)
        return ref
