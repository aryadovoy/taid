from __future__ import annotations

from telethon.tl.types import MessageReplyHeader

from taid.infra.telethon_adapter import reply_context


def test_no_reply_header_yields_none() -> None:
    assert reply_context(None) == (None, None)


def test_topic_marker_without_top_id_uses_msg_id_as_topic() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=5)

    assert reply_context(header) == (5, None)


def test_forum_reply_keeps_topic_and_reply() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=5, reply_to_top_id=7)

    assert reply_context(header) == (7, 5)


def test_forum_plain_post_pointing_at_topic_root_has_no_reply() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=7, reply_to_top_id=7)

    assert reply_context(header) == (7, None)


def test_real_reply_in_topic_keeps_topic_and_reply() -> None:
    header = MessageReplyHeader(reply_to_top_id=7, reply_to_msg_id=10)

    assert reply_context(header) == (7, 10)


def test_general_topic_marker_uses_top_id_one() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_top_id=1)

    assert reply_context(header) == (1, None)


def test_non_forum_reply_has_no_topic() -> None:
    header = MessageReplyHeader(reply_to_msg_id=3)

    assert reply_context(header) == (None, 3)
