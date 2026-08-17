from __future__ import annotations

import json

from openai import APIError, AsyncOpenAI

from ..core.models import Action, Intent
from ..devices.registry import DeviceRegistry
from .base import IntentParseError
from .prompt import build_system_prompt
from .schema import build_response_format


class OpenAICompatParser:
    def __init__(
        self,
        registry: DeviceRegistry,
        api_key: str,
        model: str,
        base_url: str | None = None,
        use_structured_output: bool = True,
        max_tokens: int = 1024,
        reasoning_effort: str | None = "low",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._system_prompt = build_system_prompt(registry)
        self._response_format = build_response_format(registry) if use_structured_output else None
        self._max_tokens = max_tokens
        self._reasoning_effort = reasoning_effort

    async def parse(self, text: str) -> Intent:
        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "max_tokens": self._max_tokens,
        }
        if self._response_format is not None:
            kwargs["response_format"] = self._response_format
        if self._reasoning_effort:
            kwargs["reasoning_effort"] = self._reasoning_effort

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except APIError as exc:
            if self._reasoning_effort and "reasoning_effort" in str(exc):
                kwargs.pop("reasoning_effort")
                try:
                    response = await self._client.chat.completions.create(**kwargs)
                except APIError as retry_exc:
                    raise IntentParseError(f"Model provider error: {retry_exc}") from retry_exc
            else:
                raise IntentParseError(f"Model provider error: {exc}") from exc

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise IntentParseError("Model returned an empty response.")

        return self._to_intent(content, text)

    @staticmethod
    def _to_intent(content: str, raw_text: str) -> Intent:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise IntentParseError(f"Model returned invalid JSON: {content[:200]}") from exc

        try:
            action = Action(payload.get("action", "unknown"))
        except ValueError:
            action = Action.UNKNOWN

        device_id = payload.get("device_id")
        if device_id is not None and not isinstance(device_id, str):
            device_id = None

        return Intent(
            action=action,
            device_id=device_id,
            is_device_command=bool(payload.get("is_device_command", True)),
            raw_text=raw_text,
        )
