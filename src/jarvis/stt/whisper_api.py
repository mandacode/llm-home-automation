from __future__ import annotations

from openai import APIError, AsyncOpenAI

from .base import TranscriptionError


class WhisperApiTranscriber:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        language: str = "pl",
        vocabulary_hint: str | None = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._language = language
        self._vocabulary_hint = vocabulary_hint

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str:
        extra = {"prompt": self._vocabulary_hint} if self._vocabulary_hint else {}
        try:
            result = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(filename, audio),
                language=self._language,
                temperature=0,
                **extra,
            )
        except APIError as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

        text = (result.text or "").strip()
        if not text:
            raise TranscriptionError("Transcription returned no text.")
        return text
