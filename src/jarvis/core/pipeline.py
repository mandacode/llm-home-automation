from __future__ import annotations

import logging

from ..devices.base import DeviceAdapter, DeviceError
from ..devices.registry import DeviceRegistry
from ..llm.base import IntentParseError, IntentParser
from ..stt.base import Transcriber, TranscriptionError
from .models import Action, ActionResult, Device

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        transcriber: Transcriber,
        parser: IntentParser,
        registry: DeviceRegistry,
        adapters: dict[str, DeviceAdapter],
    ) -> None:
        self._transcriber = transcriber
        self._parser = parser
        self._registry = registry
        self._adapters = adapters

    async def handle_voice(self, audio: bytes, filename: str = "voice.ogg") -> ActionResult:
        try:
            text = await self._transcriber.transcribe(audio, filename)
        except TranscriptionError as exc:
            logger.warning("Transcription failed: %s", exc)
            return ActionResult.failure("🎤 Nie zrozumiałem nagrania. Spróbuj jeszcze raz.")

        logger.info("Transcript: %r", text)
        return await self.handle_text(text)

    async def handle_text(self, text: str) -> ActionResult:
        try:
            intent = await self._parser.parse(text)
        except IntentParseError as exc:
            logger.warning("Intent parsing failed: %s", exc)
            return ActionResult.failure("🤖 Model chwilowo nie odpowiada. Spróbuj za moment.")

        logger.info(
            "Intent: action=%s device_id=%r is_device_command=%s",
            intent.action,
            intent.device_id,
            intent.is_device_command,
        )

        if not intent.is_device_command:
            return ActionResult.failure(f'❓ Nie zrozumiałem polecenia: „{text}"')

        device = self._registry.resolve(intent.device_id)
        if device is None:
            logger.info("Rejected unknown device_id: %r", intent.device_id)
            known = "\n".join(f"• {d.name}" for d in self._registry.all())
            return ActionResult.failure(
                f'❌ Nie znam takiego urządzenia (usłyszałem: „{text}").\n\nZnam tylko:\n{known}'
            )

        if intent.action is Action.UNKNOWN:
            return ActionResult.failure(f'❓ Nie wiem, co zrobić z „{device.name}".')

        return await self._execute(intent.action, device)

    async def _execute(self, action: Action, device: Device) -> ActionResult:
        adapter = self._adapters.get(device.type)
        if adapter is None:
            logger.error("No adapter registered for device type %r", device.type)
            return ActionResult.failure(f"⚠️ Nie mam sterownika do urządzeń typu {device.type}.")

        operation = {
            Action.TURN_ON: adapter.turn_on,
            Action.TURN_OFF: adapter.turn_off,
            Action.TOGGLE: adapter.toggle,
            Action.STATUS: adapter.status,
        }[action]

        try:
            message = await operation(device)
        except DeviceError as exc:
            logger.warning("Device %s unreachable: %s", device.id, exc)
            return ActionResult.failure(f"⚠️ {exc}")

        return ActionResult.success(message, device)
