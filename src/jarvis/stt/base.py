from __future__ import annotations

from typing import Protocol, runtime_checkable


class TranscriptionError(RuntimeError):
    pass


@runtime_checkable
class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str: ...
