from __future__ import annotations

from telethon.tl.types import MessageReplyHeader, MessageReplyStoryHeader, PeerUser

from taid.infra.telethon_adapter import ReplyContext, reply_context


def test_no_reply_header_yields_none() -> None:
    assert reply_context(None) == ReplyContext()


def test_story_reply_yields_no_message_reply_context() -> None:
    header = MessageReplyStoryHeader(peer=PeerUser(user_id=1), story_id=2)

    assert reply_context(header) == ReplyContext()


def test_topic_marker_without_top_id_uses_msg_id_as_topic() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=5)

    assert reply_context(header) == ReplyContext(topic_id=5)


def test_forum_reply_keeps_topic_and_reply() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=5, reply_to_top_id=7)

    assert reply_context(header) == ReplyContext(topic_id=7, replied_message_id=5)


def test_forum_plain_post_pointing_at_topic_root_has_no_reply() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_msg_id=7, reply_to_top_id=7)

    assert reply_context(header) == ReplyContext(topic_id=7)


def test_real_reply_in_topic_keeps_topic_and_reply() -> None:
    header = MessageReplyHeader(reply_to_top_id=7, reply_to_msg_id=10)

    assert reply_context(header) == ReplyContext(topic_id=7, replied_message_id=10)


def test_general_topic_marker_uses_top_id_one() -> None:
    header = MessageReplyHeader(forum_topic=True, reply_to_top_id=1)

    assert reply_context(header) == ReplyContext(topic_id=1)


def test_non_forum_reply_has_no_topic() -> None:
    header = MessageReplyHeader(reply_to_msg_id=3)

    assert reply_context(header) == ReplyContext(replied_message_id=3)


def test_whole_message_reply_has_no_quote() -> None:
    header = MessageReplyHeader(reply_to_msg_id=10)

    assert reply_context(header) == ReplyContext(replied_message_id=10)


def test_quoted_reply_extracts_quote_text() -> None:
    header = MessageReplyHeader(
        reply_to_msg_id=10, quote=True, quote_text="как там EURC завести?", quote_offset=40
    )

    assert reply_context(header) == ReplyContext(
        replied_message_id=10, quote="как там EURC завести?"
    )
