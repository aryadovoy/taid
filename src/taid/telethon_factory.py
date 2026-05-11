from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

# pyright: reportGeneralTypeIssues=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false
#
# This module is the only place that touches Telethon's syncified lifecycle
# methods (``start``/``run_until_disconnected``/``disconnect``/``get_me``).
# Their inline annotations don't reflect that they return coroutines when an
# event loop is already running, so the diagnostics above are relaxed here.
from telethon import TelegramClient

if TYPE_CHECKING:
    from taid.settings import TelegramConfig

logger = logging.getLogger(__name__)


def create_client(settings: TelegramConfig) -> TelegramClient:
    return TelegramClient(
        str(settings.session_path),
        settings.api_id,
        settings.api_hash.get_secret_value(),
    )


async def serve(client: TelegramClient, stop: asyncio.Event) -> None:
    await client.start()
    user = await client.get_me()
    logger.info("logged in as @%s (id=%s)", user.username or "?", user.id)

    disconnect = asyncio.ensure_future(client.run_until_disconnected())
    wait_stop = asyncio.ensure_future(stop.wait())
    await asyncio.wait({disconnect, wait_stop}, return_when=asyncio.FIRST_COMPLETED)

    for task in (wait_stop, disconnect):
        if not task.done():
            task.cancel()
    await asyncio.gather(wait_stop, disconnect, return_exceptions=True)
    await client.disconnect()
