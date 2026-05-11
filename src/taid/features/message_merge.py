from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from telethon import events
from telethon.errors import (
    MessageAuthorRequiredError,
    MessageEditTimeExpiredError,
    MessageIdInvalidError,
    MessageNotModifiedError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from taid.models import MessageRef, MessageSnapshot
    from taid.ports import TelegramClientPort, TelegramPort
    from taid.sent_registry import SentMessageRegistry
    from taid.settings import MergeConfig

logger = logging.getLogger(__name__)

_EDIT_REJECTED_ERRORS = (
    MessageAuthorRequiredError,
    MessageEditTimeExpiredError,
    MessageIdInvalidError,
    MessageNotModifiedError,
)


class MergeAction(StrEnum):
    NOOP = auto()
    MERGE = auto()
    EDIT_CURRENT = auto()


@dataclass(frozen=True, slots=True)
class MergeDecision:
    action: MergeAction
    base_ref: MessageRef | None = None
    merged_text: str | None = None
    current_text: str | None = None


@dataclass(slots=True)
class _MergeSession:
    base_ref: MessageRef
    base_text: str
    last_event_at: datetime
    replied_message_id: int | None


type _SessionKey = tuple[int, int | None]


def _session_key(message: MessageSnapshot) -> _SessionKey:
    return message.ref.chat_id, message.topic_id


def _replies_conflict(a: int | None, b: int | None) -> bool:
    return b is not None and a != b


class MessageMergeService:
    def __init__(self, settings: MergeConfig) -> None:
        self._settings = settings
        self._sessions: dict[_SessionKey, _MergeSession] = {}

    def handle_outgoing(  # noqa: PLR0911
        self, message: MessageSnapshot, *, now: datetime | None = None
    ) -> MergeDecision:
        if not self._settings.enabled:
            return MergeDecision(MergeAction.NOOP)

        now = now or datetime.now(UTC)
        msg_time = message.date or now
        key = _session_key(message)
        text = message.text or ""

        if not message.is_plain_text_outgoing:
            self._sessions.pop(key, None)
            return MergeDecision(MergeAction.NOOP)

        if text.startswith(self._settings.break_prefix):
            clean_text = text.removeprefix(self._settings.break_prefix)
            self._sessions[key] = _MergeSession(
                message.ref, clean_text, msg_time, message.replied_message_id
            )
            return MergeDecision(MergeAction.EDIT_CURRENT, current_text=clean_text)

        if message.date is not None and (now - message.date) > timedelta(
            seconds=self._settings.timeout_seconds
        ):
            return MergeDecision(MergeAction.NOOP)

        session = self._sessions.get(key)
        if session is None or msg_time - session.last_event_at > timedelta(
            seconds=self._settings.timeout_seconds
        ):
            self._sessions[key] = _MergeSession(
                message.ref, text, msg_time, message.replied_message_id
            )
            return MergeDecision(MergeAction.NOOP)

        if _replies_conflict(session.replied_message_id, message.replied_message_id):
            self._sessions[key] = _MergeSession(
                message.ref, text, msg_time, message.replied_message_id
            )
            return MergeDecision(MergeAction.NOOP)

        merged_text = f"{session.base_text}\n{text}"
        replied_id = message.replied_message_id or session.replied_message_id
        self._sessions[key] = _MergeSession(session.base_ref, merged_text, msg_time, replied_id)
        return MergeDecision(MergeAction.MERGE, base_ref=session.base_ref, merged_text=merged_text)

    def handle_incoming(self, message: MessageSnapshot) -> None:
        if not message.outgoing:
            self._sessions.pop(_session_key(message), None)

    def handle_edited(self, message: MessageSnapshot, *, now: datetime | None = None) -> None:
        if not message.outgoing or message.text is None:
            return

        key = _session_key(message)
        session = self._sessions.get(key)
        if session is None or session.base_ref != message.ref:
            return

        now = now or datetime.now(UTC)
        if now - session.last_event_at > timedelta(seconds=self._settings.timeout_seconds):
            del self._sessions[key]
            logger.debug("merge: session for base %s expired, dropped", message.ref.message_id)
            return

        self._sessions[key] = _MergeSession(
            base_ref=session.base_ref,
            base_text=message.text,
            last_event_at=now,
            replied_message_id=session.replied_message_id,
        )
        logger.debug("merge: base %s updated to new text", message.ref.message_id)

    def rebase(self, message: MessageSnapshot, *, now: datetime | None = None) -> None:
        self._sessions[_session_key(message)] = _MergeSession(
            base_ref=message.ref,
            base_text=message.text or "",
            last_event_at=now or datetime.now(UTC),
            replied_message_id=message.replied_message_id,
        )


class MessageMergeHandler:
    def __init__(
        self,
        settings: MergeConfig,
        service: MessageMergeService,
        telegram: TelegramPort,
        sent_registry: SentMessageRegistry,
        *,
        merge_exempt: Callable[[MessageSnapshot], bool] | None = None,
    ) -> None:
        self._settings = settings
        self._service = service
        self._telegram = telegram
        self._sent_registry = sent_registry
        self._merge_exempt = merge_exempt
        self._locks: dict[_SessionKey, asyncio.Lock] = {}

    def register(self, client: TelegramClientPort) -> None:
        if not self._settings.enabled:
            return

        async def on_new_message(event: events.NewMessage.Event) -> None:
            snapshot = self._telegram.snapshot(event)
            if snapshot.outgoing and self._skips_merge(snapshot):
                return
            lock = self._lock_for(_session_key(snapshot))
            async with lock:
                if not snapshot.outgoing:
                    self._service.handle_incoming(snapshot)
                    return

                decision = self._service.handle_outgoing(snapshot)
                await self._apply_decision(decision, snapshot)

        async def on_message_edited(event: events.NewMessage.Event) -> None:
            snapshot = self._telegram.snapshot(event)
            lock = self._lock_for(_session_key(snapshot))
            async with lock:
                self._service.handle_edited(snapshot)

        client.add_event_handler(on_new_message, events.NewMessage())
        client.add_event_handler(on_message_edited, events.MessageEdited())

    async def _apply_decision(self, decision: MergeDecision, snapshot: MessageSnapshot) -> None:
        if decision.action is MergeAction.EDIT_CURRENT and decision.current_text is not None:
            await self._telegram.edit_message(snapshot.ref, decision.current_text)
            logger.debug("merge: stripped break prefix in chat %s", snapshot.ref.chat_id)
        elif (
            decision.action is MergeAction.MERGE
            and decision.base_ref is not None
            and decision.merged_text is not None
        ):
            try:
                await self._telegram.edit_message(decision.base_ref, decision.merged_text)
            except _EDIT_REJECTED_ERRORS:
                logger.debug(
                    "merge: base %s no longer editable, re-basing on %s in chat %s",
                    decision.base_ref.message_id,
                    snapshot.ref.message_id,
                    snapshot.ref.chat_id,
                )
                self._service.rebase(snapshot)
                return
            except Exception:
                logger.warning(
                    "merge: edit of base %s failed, re-basing on %s in chat %s",
                    decision.base_ref.message_id,
                    snapshot.ref.message_id,
                    snapshot.ref.chat_id,
                    exc_info=True,
                )
                self._service.rebase(snapshot)
                return
            try:
                await self._telegram.delete_message(snapshot.ref)
            except Exception:
                logger.warning(
                    "merge: failed to delete %s after merging into %s in chat %s, text duplicated",
                    snapshot.ref.message_id,
                    decision.base_ref.message_id,
                    snapshot.ref.chat_id,
                    exc_info=True,
                )
                return
            logger.info(
                "merge: message %s merged into %s in chat %s",
                snapshot.ref.message_id,
                decision.base_ref.message_id,
                snapshot.ref.chat_id,
            )

    def _skips_merge(self, snapshot: MessageSnapshot) -> bool:
        if snapshot.ref in self._sent_registry:
            return True
        return self._merge_exempt is not None and self._merge_exempt(snapshot)

    def _lock_for(self, key: _SessionKey) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
