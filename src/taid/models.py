from dataclasses import dataclass
from datetime import datetime

ChatRef = int | str


@dataclass(frozen=True, slots=True)
class MessageRef:
    chat_id: int
    message_id: int


@dataclass(frozen=True, slots=True)
class MessageSnapshot:
    ref: MessageRef
    text: str | None
    outgoing: bool
    has_media: bool = False
    is_forward: bool = False
    replied_message_id: int | None = None
    reply_quote: str | None = None
    topic_id: int | None = None
    has_buttons: bool = False
    grouped_id: int | None = None
    date: datetime | None = None

    @property
    def is_plain_text_outgoing(self) -> bool:
        return (
            self.outgoing
            and self.text is not None
            and self.text != ""
            and not self.has_media
            and not self.is_forward
            and not self.has_buttons
            and self.grouped_id is None
        )
