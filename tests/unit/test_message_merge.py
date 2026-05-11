from __future__ import annotations

from datetime import UTC, datetime, timedelta

from taid.features.message_merge import MergeAction, MessageMergeService
from taid.settings import MergeConfig
from tests.conftest import make_snapshot


def test_merges_plain_messages_in_same_chat() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert service.handle_outgoing(make_snapshot("one"), now=now).action is MergeAction.NOOP
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2), now=now + timedelta(seconds=1)
    )

    assert decision.action is MergeAction.MERGE
    assert decision.base_ref is not None
    assert decision.base_ref.message_id == 1
    assert decision.merged_text == "one\ntwo"


def test_different_chats_do_not_share_state() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", chat_id=1), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", chat_id=2), now=now + timedelta(seconds=1)
    )

    assert decision.action is MergeAction.NOOP


def test_different_topics_in_same_chat_do_not_share_state() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", chat_id=10, topic_id=1), now=now)
    decision_other = service.handle_outgoing(
        make_snapshot("two", chat_id=10, message_id=2, topic_id=2), now=now + timedelta(seconds=1)
    )

    assert decision_other.action is MergeAction.NOOP

    decision_same_topic = service.handle_outgoing(
        make_snapshot("three", chat_id=10, message_id=3, topic_id=1), now=now + timedelta(seconds=2)
    )

    assert decision_same_topic.action is MergeAction.MERGE
    assert decision_same_topic.merged_text == "one\nthree"


def test_topic_marker_message_is_plain_text() -> None:
    assert make_snapshot("hi", topic_id=5).is_plain_text_outgoing is True


def test_real_reply_in_topic_is_plain_text() -> None:
    assert make_snapshot("hi", topic_id=5, replied_message_id=99).is_plain_text_outgoing is True


def test_replies_to_same_message_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", replied_message_id=42), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2, replied_message_id=42),
        now=now + timedelta(seconds=1),
    )

    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "one\ntwo"


def test_replies_to_different_messages_do_not_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", replied_message_id=42), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2, replied_message_id=99),
        now=now + timedelta(seconds=1),
    )

    assert decision.action is MergeAction.NOOP


def test_reply_and_plain_message_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", replied_message_id=42), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2), now=now + timedelta(seconds=1)
    )

    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "one\ntwo"


def test_plain_base_then_reply_does_not_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one"), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2, replied_message_id=42),
        now=now + timedelta(seconds=1),
    )

    assert decision.action is MergeAction.NOOP


def test_incoming_message_breaks_same_topic_only() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", chat_id=10, topic_id=1), now=now)
    service.handle_outgoing(make_snapshot("alpha", chat_id=10, topic_id=2), now=now)
    service.handle_incoming(make_snapshot("incoming", chat_id=10, topic_id=1, outgoing=False))

    assert (
        service.handle_outgoing(
            make_snapshot("two", chat_id=10, message_id=2, topic_id=1), now=now
        ).action
        is MergeAction.NOOP
    )
    decision = service.handle_outgoing(
        make_snapshot("beta", chat_id=10, message_id=2, topic_id=2), now=now
    )
    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "alpha\nbeta"


def test_non_plain_message_breaks_session() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one"), now=now)
    service.handle_outgoing(
        make_snapshot("photo", message_id=2, has_media=True), now=now + timedelta(seconds=1)
    )
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=3), now=now + timedelta(seconds=2)
    )

    assert decision.action is MergeAction.NOOP


def test_incoming_message_breaks_same_chat_only() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", chat_id=1), now=now)
    service.handle_outgoing(make_snapshot("alpha", chat_id=2), now=now)
    service.handle_incoming(make_snapshot("incoming", chat_id=1, outgoing=False))

    assert (
        service.handle_outgoing(make_snapshot("two", chat_id=1, message_id=2), now=now).action
        is MergeAction.NOOP
    )
    decision = service.handle_outgoing(make_snapshot("beta", chat_id=2, message_id=2), now=now)
    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "alpha\nbeta"


def test_manual_edit_becomes_next_baseline() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", message_id=1), now=now)
    service.handle_outgoing(make_snapshot("two", message_id=2), now=now + timedelta(seconds=1))
    service.handle_edited(make_snapshot("edited", message_id=1), now=now + timedelta(seconds=2))
    decision = service.handle_outgoing(
        make_snapshot("three", message_id=3), now=now + timedelta(seconds=3)
    )

    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "edited\nthree"


def test_manual_edit_after_chain_uses_edited_text() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", message_id=1), now=now)
    service.handle_outgoing(make_snapshot("two", message_id=2), now=now + timedelta(seconds=1))
    service.handle_outgoing(make_snapshot("three", message_id=3), now=now + timedelta(seconds=2))
    service.handle_edited(make_snapshot("CUSTOM", message_id=1), now=now + timedelta(seconds=3))
    decision = service.handle_outgoing(
        make_snapshot("four", message_id=4), now=now + timedelta(seconds=4)
    )

    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "CUSTOM\nfour"


def test_edit_after_timeout_drops_stale_session() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", message_id=1), now=now)
    service.handle_edited(make_snapshot("edited", message_id=1), now=now + timedelta(hours=1))
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2), now=now + timedelta(hours=1, seconds=1)
    )

    assert decision.action is MergeAction.NOOP


def test_break_prefix_makes_independent_message() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30, break_prefix=". "))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", message_id=1), now=now)
    decision = service.handle_outgoing(
        make_snapshot(". two", message_id=2), now=now + timedelta(seconds=1)
    )

    assert decision.action is MergeAction.EDIT_CURRENT
    assert decision.current_text == "two"


def test_timeout_breaks_session() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one"), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2), now=now + timedelta(seconds=31)
    )

    assert decision.action is MergeAction.NOOP


def test_disabled_service_never_merges() -> None:
    service = MessageMergeService(MergeConfig(enabled=False, timeout_seconds=30))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one"), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2), now=now + timedelta(seconds=1)
    )

    assert decision.action is MergeAction.NOOP


def test_stale_message_does_not_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    old = now - timedelta(hours=1)

    service.handle_outgoing(make_snapshot("base", date=now), now=now)
    decision = service.handle_outgoing(make_snapshot("late", message_id=2, date=old), now=now)

    assert decision.action is MergeAction.NOOP


def test_two_stale_messages_do_not_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    old = now - timedelta(hours=1)

    first = service.handle_outgoing(make_snapshot("a", date=old), now=now)
    second = service.handle_outgoing(
        make_snapshot("b", message_id=2, date=old + timedelta(seconds=5)), now=now
    )

    assert first.action is MergeAction.NOOP
    assert second.action is MergeAction.NOOP


def test_fresh_messages_with_close_dates_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", date=now), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2, date=now + timedelta(seconds=5)), now=now
    )

    assert decision.action is MergeAction.MERGE
    assert decision.merged_text == "one\ntwo"


def test_fresh_messages_with_far_apart_dates_do_not_merge() -> None:
    service = MessageMergeService(MergeConfig(timeout_seconds=30))
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    service.handle_outgoing(make_snapshot("one", date=now), now=now)
    decision = service.handle_outgoing(
        make_snapshot("two", message_id=2, date=now + timedelta(minutes=5)), now=now
    )

    assert decision.action is MergeAction.NOOP
