from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from taid.models import MessageRef


class SentMessageRegistry:
    """Recent messages sent by taid itself, so feature handlers can skip them.

    Bounded: oldest refs are evicted once ``max_size`` is exceeded, which keeps
    memory flat for a long-running process.
    """

    def __init__(self, max_size: int = 256) -> None:
        self._max_size = max_size
        self._refs: OrderedDict[MessageRef, None] = OrderedDict()

    def add(self, ref: MessageRef) -> None:
        self._refs[ref] = None
        while len(self._refs) > self._max_size:
            self._refs.popitem(last=False)

    def __contains__(self, ref: MessageRef) -> bool:
        return ref in self._refs
