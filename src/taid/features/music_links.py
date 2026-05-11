from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from telethon import events

if TYPE_CHECKING:
    from taid.models import ChatRef, MessageSnapshot
    from taid.ports import TelegramClientPort, TelegramPort
    from taid.sent_registry import SentMessageRegistry
    from taid.settings import MusicLinkConfig

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class MusicLinkRequest:
    request_id: uuid.UUID
    original_chat: ChatRef
    original_topic_id: int | None
    url: str
    created_at: datetime
    sent_message_id: int


class MusicLinkService:
    def __init__(self, settings: MusicLinkConfig) -> None:
        self._settings = settings
        self._pending: OrderedDict[int, MusicLinkRequest] = OrderedDict()

    def first_supported_url(self, text: str | None) -> str | None:
        if not text:
            return None

        domains = {domain.lower() for domain in self._settings.domains}
        for match in _URL_RE.finditer(text):
            url = match.group(0).rstrip(".,;:!?)")
            host = urlparse(url).hostname
            if host and host.lower() in domains:
                return url
        return None

    def enqueue(
        self, chat: ChatRef, url: str, *, sent_message_id: int, topic_id: int | None = None
    ) -> MusicLinkRequest:
        request = MusicLinkRequest(
            request_id=uuid.uuid4(),
            original_chat=chat,
            original_topic_id=topic_id,
            url=url,
            created_at=datetime.now(UTC),
            sent_message_id=sent_message_id,
        )
        self._pending[sent_message_id] = request
        return request

    def match_response(self, replied_message_id: int | None) -> MusicLinkRequest | None:
        if replied_message_id is not None:
            return self._pending.pop(replied_message_id, None)
        if self._pending:
            _, request = self._pending.popitem(last=False)
            return request
        return None

    def remove(self, request_id: uuid.UUID) -> MusicLinkRequest | None:
        for request in tuple(self._pending.values()):
            if request.request_id == request_id:
                del self._pending[request.sent_message_id]
                return request
        return None


class MusicLinkHandler:
    def __init__(
        self,
        settings: MusicLinkConfig,
        service: MusicLinkService,
        telegram: TelegramPort,
        sent_registry: SentMessageRegistry,
    ) -> None:
        self._settings = settings
        self._service = service
        self._telegram = telegram
        self._sent_registry = sent_registry
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    def register(self, client: TelegramClientPort) -> None:
        if not self._settings.enabled:
            return

        async def on_outgoing(event: events.NewMessage.Event) -> None:
            snapshot = self._telegram.snapshot(event)
            await self._handle_outgoing(snapshot)

        async def on_bot_response(event: events.NewMessage.Event) -> None:
            snapshot = self._telegram.snapshot(event)
            await self._handle_bot_response(snapshot)

        client.add_event_handler(on_outgoing, events.NewMessage(outgoing=True))
        client.add_event_handler(
            on_bot_response,
            events.NewMessage(incoming=True, from_users=self._settings.bot_username),
        )

    async def _handle_outgoing(self, snapshot: MessageSnapshot) -> None:
        if snapshot.ref in self._sent_registry:
            return

        url = self._service.first_supported_url(snapshot.text)
        if url is None:
            return

        sent_ref = await self._telegram.send_message(self._settings.bot_username, url)
        async with self._lock:
            request = self._service.enqueue(
                snapshot.ref.chat_id,
                url,
                sent_message_id=sent_ref.message_id,
                topic_id=snapshot.topic_id,
            )
        await self._telegram.delete_message(snapshot.ref)
        task = asyncio.create_task(self._expire(request.request_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        logger.info("music: forwarded %s to @%s", url, self._settings.bot_username)

    async def _handle_bot_response(self, snapshot: MessageSnapshot) -> None:
        async with self._lock:
            request = self._service.match_response(snapshot.replied_message_id)

        if request is None:
            return

        text = snapshot.text or f"@{self._settings.bot_username} returned an empty response."
        await self._telegram.send_message(
            request.original_chat, text, reply_to=request.original_topic_id
        )
        logger.info("music: delivered result for %s to chat %s", request.url, request.original_chat)

    async def _expire(self, request_id: uuid.UUID) -> None:
        await asyncio.sleep(self._settings.timeout_seconds)

        async with self._lock:
            request = self._service.remove(request_id)

        if request is None:
            return

        await self._telegram.send_message(
            self._settings.error_chat,
            f"@{self._settings.bot_username} did not respond in time for {request.url}",
            reply_to=request.original_topic_id,
        )
        logger.warning("music: timed out waiting for %s", request.url)
