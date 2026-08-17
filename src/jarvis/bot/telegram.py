from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..core.pipeline import Pipeline
from ..devices.registry import DeviceRegistry

logger = logging.getLogger(__name__)

MAX_VOICE_BYTES = 5 * 1024 * 1024


class TelegramBot:
    def __init__(
        self,
        token: str,
        pipeline: Pipeline,
        registry: DeviceRegistry,
        allowed_user_ids: frozenset[int],
    ) -> None:
        self._pipeline = pipeline
        self._registry = registry
        self._allowed = allowed_user_ids
        self._app = Application.builder().token(token).build()
        self._register_handlers()

        if not allowed_user_ids:
            logger.warning(
                "TELEGRAM_ALLOWED_USER_IDS is empty — the bot will reject everyone (fail-closed)."
            )

    def _register_handlers(self) -> None:
        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(CommandHandler("devices", self._on_devices))
        self._app.add_handler(MessageHandler(filters.VOICE, self._on_voice))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

    def _is_allowed(self, update: Update) -> bool:
        user = update.effective_user
        return bool(user and user.id in self._allowed)

    async def _reject(self, update: Update) -> None:
        user = update.effective_user
        logger.warning("Rejected unauthorized user: id=%s", user.id if user else "?")
        if update.message:
            await update.message.reply_text("⛔ Brak dostępu.")

    async def _on_start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return await self._reject(update)
        await update.message.reply_text(
            "🏠 Cześć! Nagraj głosówkę z poleceniem, np. „włącz pączka”.\n"
            "/devices — lista urządzeń"
        )

    async def _on_devices(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return await self._reject(update)
        lines = [f"• {d.name} (`{d.id}`)" for d in self._registry.all()]
        await update.message.reply_text(
            "Znane urządzenia:\n" + "\n".join(lines), parse_mode="Markdown"
        )

    async def _on_voice(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return await self._reject(update)

        voice = update.message.voice
        if voice.file_size and voice.file_size > MAX_VOICE_BYTES:
            await update.message.reply_text("🎤 Nagranie za długie. Powiedz krócej.")
            return

        await update.message.chat.send_action("typing")

        telegram_file = await voice.get_file()
        audio = bytes(await telegram_file.download_as_bytearray())

        result = await self._pipeline.handle_voice(audio, filename="voice.ogg")
        await update.message.reply_text(result.message)

    async def _on_text(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update):
            return await self._reject(update)

        await update.message.chat.send_action("typing")
        result = await self._pipeline.handle_text(update.message.text)
        await update.message.reply_text(result.message)

    def run(self) -> None:
        logger.info("Bot started. Devices in registry: %d", len(self._registry))
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)
