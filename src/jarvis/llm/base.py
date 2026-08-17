from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..core.models import Intent


class IntentParseError(RuntimeError):
    pass


@runtime_checkable
class IntentParser(Protocol):
    async def parse(self, text: str) -> Intent: ...
