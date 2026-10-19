from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import pytest

from taid.errors import SnapshotError
from taid.infra.telethon_events import with_snapshot
from tests.conftest import FakeEvent, FakeMessage, FakeTelegramPort

if TYPE_CHECKING:
    from telethon.events import NewMessage

    from taid.models import MessageSnapshot


async def test_with_snapshot_does_not_suppress_callback_snapshot_error() -> None:
    telegram = FakeTelegramPort()

    @with_snapshot(telegram, logging.getLogger(__name__), "test")
    async def callback(snapshot: MessageSnapshot) -> None:
        raise SnapshotError(str(snapshot.ref.message_id))

    event = FakeEvent(chat_id=1, message_id=2, message=FakeMessage("message"))

    with pytest.raises(SnapshotError, match="2"):
        await callback(cast("NewMessage.Event", event))
