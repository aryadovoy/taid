from __future__ import annotations

import asyncio
import logging
import signal
from typing import TYPE_CHECKING

from taid import __version__
from taid.features.message_merge import MessageMergeHandler, MessageMergeService
from taid.features.music_links import MusicLinkHandler, MusicLinkService
from taid.infra.telethon_adapter import TelethonAdapter
from taid.logging_setup import configure_logging
from taid.sent_registry import SentMessageRegistry
from taid.settings import Config
from taid.telethon_factory import create_client, serve

if TYPE_CHECKING:
    from taid.models import MessageSnapshot

logger = logging.getLogger(__name__)


async def _start(config: Config) -> None:
    client = create_client(config.telegram)
    sent_registry = SentMessageRegistry()
    telegram = TelethonAdapter(client, sent_registry)
    music_service = MusicLinkService(config.music_links)

    def has_music_link(snapshot: MessageSnapshot) -> bool:
        return (
            config.music_links.enabled
            and music_service.first_supported_url(snapshot.text) is not None
        )

    MessageMergeHandler(
        config.merge,
        MessageMergeService(config.merge),
        telegram,
        sent_registry,
        merge_exempt=has_music_link,
    ).register(client)
    MusicLinkHandler(
        config.music_links,
        music_service,
        telegram,
        sent_registry,
    ).register(client)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    logger.info("taid %s starting", __version__)
    await serve(client, stop)
    logger.info("taid stopped")


def run() -> None:
    config = Config()
    configure_logging(config.app.log_level)
    try:
        asyncio.run(_start(config))
    except KeyboardInterrupt:
        logger.info("taid stopped")
