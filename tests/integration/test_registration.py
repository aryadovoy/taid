from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from telethon import events

from taid.features.message_merge import MessageMergeHandler, MessageMergeService
from taid.features.music_links import MusicLinkHandler, MusicLinkService
from taid.models import MessageRef
from taid.settings import MergeConfig, MusicLinkConfig
from tests.conftest import FakeEvent, FakeMessage, FakeTelegramPort


@dataclass
class FakeClient:
    handlers: list[tuple[Any, Any]] = field(default_factory=list)

    def add_event_handler(self, callback: Any, event: Any = None) -> None:
        self.handlers.append((callback, event))


def test_merge_registers_two_handlers_when_enabled() -> None:
    client = FakeClient()
    settings = MergeConfig(enabled=True)
    port = FakeTelegramPort()
    MessageMergeHandler(settings, MessageMergeService(settings), port, port.sent_registry).register(
        client
    )

    builder_types = [type(event) for _, event in client.handlers]
    assert events.NewMessage in builder_types
    assert events.MessageEdited in builder_types


def test_merge_registers_nothing_when_disabled() -> None:
    client = FakeClient()
    settings = MergeConfig(enabled=False)
    port = FakeTelegramPort()
    MessageMergeHandler(settings, MessageMergeService(settings), port, port.sent_registry).register(
        client
    )

    assert client.handlers == []


def test_music_registers_two_handlers_when_enabled() -> None:
    client = FakeClient()
    settings = MusicLinkConfig(enabled=True)
    port = FakeTelegramPort()
    MusicLinkHandler(settings, MusicLinkService(settings), port, port.sent_registry).register(
        client
    )

    assert len(client.handlers) == 2
    assert all(isinstance(event, events.NewMessage) for _, event in client.handlers)


def test_music_registers_nothing_when_disabled() -> None:
    client = FakeClient()
    settings = MusicLinkConfig(enabled=False)
    port = FakeTelegramPort()
    MusicLinkHandler(settings, MusicLinkService(settings), port, port.sent_registry).register(
        client
    )

    assert client.handlers == []


async def test_merge_flow_edits_base_and_deletes_duplicate() -> None:
    telegram = FakeTelegramPort()
    settings = MergeConfig(enabled=True, timeout_seconds=30)
    handler = MessageMergeHandler(
        settings, MessageMergeService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    on_new = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_new(FakeEvent(chat_id=1, message_id=1, message=FakeMessage("one")))
    await on_new(FakeEvent(chat_id=1, message_id=2, message=FakeMessage("two")))

    assert telegram.edits == [(MessageRef(chat_id=1, message_id=1), "one\ntwo")]
    assert telegram.deletes == [MessageRef(chat_id=1, message_id=2)]


async def test_merge_rebases_when_base_was_deleted() -> None:
    @dataclass
    class RaisingEditPort(FakeTelegramPort):
        gone: MessageRef | None = None

        async def edit_message(self, ref: MessageRef, text: str) -> None:
            if self.gone is not None and ref == self.gone:
                raise RuntimeError("message deleted")
            await super().edit_message(ref, text)

    telegram = RaisingEditPort(gone=MessageRef(chat_id=1, message_id=1))
    settings = MergeConfig(enabled=True, timeout_seconds=30)
    service = MessageMergeService(settings)
    handler = MessageMergeHandler(settings, service, telegram, telegram.sent_registry)
    client = FakeClient()
    handler.register(client)

    on_new = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_new(FakeEvent(chat_id=1, message_id=1, message=FakeMessage("link")))
    await on_new(FakeEvent(chat_id=1, message_id=2, message=FakeMessage("hello")))

    assert telegram.deletes == []
    assert telegram.edits == []

    await on_new(FakeEvent(chat_id=1, message_id=3, message=FakeMessage("world")))

    assert telegram.edits == [(MessageRef(chat_id=1, message_id=2), "hello\nworld")]
    assert telegram.deletes == [MessageRef(chat_id=1, message_id=3)]


async def test_music_flow_forwards_and_delivers_response() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    outgoing_handlers = [
        cb for cb, event in client.handlers if isinstance(event, events.NewMessage)
    ]
    assert len(outgoing_handlers) == 2
    on_outgoing, on_bot_response = outgoing_handlers

    await on_outgoing(
        FakeEvent(chat_id=42, message_id=1, message=FakeMessage("https://open.spotify.com/track/1"))
    )

    assert telegram.sends[0] == ("odesli_bot", "https://open.spotify.com/track/1", None)
    assert telegram.deletes == [MessageRef(chat_id=42, message_id=1)]

    await on_bot_response(
        FakeEvent(chat_id=0, message_id=2, message=FakeMessage("converted link", out=False))
    )

    assert telegram.sends[-1] == (42, "converted link", None)

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_music_accepts_single_explicit_url_with_surrounding_text() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)
    on_outgoing = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_outgoing(
        FakeEvent(
            chat_id=42,
            message_id=1,
            message=FakeMessage("Listen to https://open.spotify.com/track/1 please"),
        )
    )

    assert telegram.sends == [("odesli_bot", "https://open.spotify.com/track/1", None)]
    assert telegram.deletes == [MessageRef(chat_id=42, message_id=1)]

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_music_ignores_forwarded_message() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)
    on_outgoing = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_outgoing(
        FakeEvent(
            chat_id=42,
            message_id=1,
            message=FakeMessage("https://open.spotify.com/track/1", forward=object()),
        )
    )

    assert telegram.sends == []
    assert telegram.deletes == []


async def test_music_ignores_message_with_multiple_explicit_urls() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)
    on_outgoing = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_outgoing(
        FakeEvent(
            chat_id=42,
            message_id=1,
            message=FakeMessage("https://open.spotify.com/track/1 https://music.yandex.ru/album/2"),
        )
    )
    await on_outgoing(
        FakeEvent(
            chat_id=42,
            message_id=2,
            message=FakeMessage("https://open.spotify.com/track/1 https://example.com/details"),
        )
    )

    assert telegram.sends == []
    assert telegram.deletes == []


async def test_music_delivers_response_into_origin_topic() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    outgoing_handlers = [
        cb for cb, event in client.handlers if isinstance(event, events.NewMessage)
    ]
    on_outgoing, on_bot_response = outgoing_handlers

    await on_outgoing(
        FakeEvent(
            chat_id=42,
            message_id=1,
            message=FakeMessage("https://open.spotify.com/track/1", topic_id=7),
        )
    )

    await on_bot_response(
        FakeEvent(chat_id=0, message_id=2, message=FakeMessage("converted link", out=False))
    )

    assert telegram.sends[-1] == (42, "converted link", 7)

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_music_forward_to_bot_does_not_loop() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    on_outgoing = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_outgoing(
        FakeEvent(chat_id=42, message_id=1, message=FakeMessage("https://open.spotify.com/track/1"))
    )
    assert len(telegram.sends) == 1

    # The forwarded message to the bot triggers on_outgoing again — must be skipped.
    sent_ref = telegram.sent_refs[0]
    await on_outgoing(
        FakeEvent(
            chat_id=sent_ref.chat_id,
            message_id=sent_ref.message_id,
            message=FakeMessage("https://open.spotify.com/track/1"),
        )
    )
    assert len(telegram.sends) == 1

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_music_delivered_response_does_not_loop() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    outgoing_handlers = [
        cb for cb, event in client.handlers if isinstance(event, events.NewMessage)
    ]
    on_outgoing, on_bot_response = outgoing_handlers

    await on_outgoing(
        FakeEvent(chat_id=42, message_id=1, message=FakeMessage("https://open.spotify.com/track/1"))
    )

    bot_response = "Song\nhttps://open.spotify.com/track/1\nhttps://music.yandex.ru/album/1"
    await on_bot_response(
        FakeEvent(chat_id=0, message_id=2, message=FakeMessage(bot_response, out=False))
    )
    assert len(telegram.sends) == 2

    # The delivered message contains supported-domain URLs — must be skipped.
    delivered_ref = telegram.sent_refs[-1]
    await on_outgoing(
        FakeEvent(
            chat_id=delivered_ref.chat_id,
            message_id=delivered_ref.message_id,
            message=FakeMessage(bot_response),
        )
    )
    assert len(telegram.sends) == 2

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_music_routes_out_of_order_responses_by_reply() -> None:
    telegram = FakeTelegramPort()
    settings = MusicLinkConfig(enabled=True, bot_username="odesli_bot")
    handler = MusicLinkHandler(
        settings, MusicLinkService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    outgoing_handlers = [
        cb for cb, event in client.handlers if isinstance(event, events.NewMessage)
    ]
    on_outgoing, on_bot_response = outgoing_handlers

    await on_outgoing(
        FakeEvent(chat_id=10, message_id=1, message=FakeMessage("https://open.spotify.com/track/1"))
    )
    await on_outgoing(
        FakeEvent(chat_id=20, message_id=1, message=FakeMessage("https://music.yandex.ru/album/2"))
    )
    first_sent, second_sent = telegram.sent_refs[:2]

    # The bot answers the second request first; replies must route by reply id.
    await on_bot_response(
        FakeEvent(
            chat_id=0,
            message_id=3,
            message=FakeMessage("second result", out=False, reply_to_msg_id=second_sent.message_id),
        )
    )
    await on_bot_response(
        FakeEvent(
            chat_id=0,
            message_id=4,
            message=FakeMessage("first result", out=False, reply_to_msg_id=first_sent.message_id),
        )
    )

    assert (20, "second result", None) in telegram.sends
    assert (10, "first result", None) in telegram.sends

    for task in asyncio.all_tasks() - {asyncio.current_task()}:
        task.cancel()


async def test_merge_skips_self_sent_messages() -> None:
    telegram = FakeTelegramPort()
    settings = MergeConfig(enabled=True, timeout_seconds=30)
    handler = MessageMergeHandler(
        settings, MessageMergeService(settings), telegram, telegram.sent_registry
    )
    client = FakeClient()
    handler.register(client)

    on_new = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_new(FakeEvent(chat_id=1, message_id=1, message=FakeMessage("one")))

    # A message taid sent itself (e.g. a delivered music result) must not merge
    # and must not disturb the ongoing session.
    self_ref = await telegram.send_message(1, "bot result")
    await on_new(
        FakeEvent(
            chat_id=self_ref.chat_id,
            message_id=self_ref.message_id,
            message=FakeMessage("bot result"),
        )
    )
    assert telegram.edits == []

    await on_new(FakeEvent(chat_id=1, message_id=3, message=FakeMessage("two")))
    assert telegram.edits == [(MessageRef(chat_id=1, message_id=1), "one\ntwo")]


async def test_merge_skips_music_link_messages() -> None:
    telegram = FakeTelegramPort()
    settings = MergeConfig(enabled=True, timeout_seconds=30)
    handler = MessageMergeHandler(
        settings,
        MessageMergeService(settings),
        telegram,
        telegram.sent_registry,
        merge_exempt=lambda snapshot: "spotify" in (snapshot.text or ""),
    )
    client = FakeClient()
    handler.register(client)

    on_new = next(cb for cb, event in client.handlers if isinstance(event, events.NewMessage))

    await on_new(FakeEvent(chat_id=1, message_id=1, message=FakeMessage("one")))
    await on_new(
        FakeEvent(chat_id=1, message_id=2, message=FakeMessage("https://open.spotify.com/track/1"))
    )
    assert telegram.edits == []

    await on_new(FakeEvent(chat_id=1, message_id=3, message=FakeMessage("two")))
    assert telegram.edits == [(MessageRef(chat_id=1, message_id=1), "one\ntwo")]
