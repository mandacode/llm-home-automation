from __future__ import annotations

import logging
import sys

from .bot.telegram import TelegramBot
from .config import ConfigError, load_config
from .core.pipeline import Pipeline
from .devices.registry import DeviceRegistry, DeviceRegistryError
from .devices.ps5 import PS5Adapter
from .devices.shelly import ShellyGen3Adapter
from .llm.openai_compat import OpenAICompatParser
from .stt.whisper_api import WhisperApiTranscriber

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def build_bot() -> TelegramBot:
    config = load_config()

    registry = DeviceRegistry.from_yaml(config.devices_config)
    logger.info("Registry loaded: %d devices — %s", len(registry), ", ".join(registry.ids()))

    transcriber = WhisperApiTranscriber(
        api_key=config.stt_api_key,
        model=config.stt_model,
        base_url=config.stt_base_url,
        language=config.stt_language,
        vocabulary_hint=registry.vocabulary_hint(),
    )

    parser = OpenAICompatParser(
        registry=registry,
        api_key=config.llm_api_key,
        model=config.llm_model,
        base_url=config.llm_base_url,
        use_structured_output=config.uses_structured_output,
        max_tokens=config.llm_max_tokens,
        reasoning_effort=config.llm_reasoning_effort,
    )

    adapters = {
        ShellyGen3Adapter.device_type: ShellyGen3Adapter(timeout_s=config.device_timeout_s),
        PS5Adapter.device_type: PS5Adapter(profile_path=config.ps5_profile_path),
    }

    pipeline = Pipeline(
        transcriber=transcriber,
        parser=parser,
        registry=registry,
        adapters=adapters,
    )

    return TelegramBot(
        token=config.telegram_token,
        pipeline=pipeline,
        registry=registry,
        allowed_user_ids=config.allowed_user_ids,
    )


def main() -> int:
    setup_logging()
    try:
        bot = build_bot()
    except (ConfigError, DeviceRegistryError) as exc:
        logger.error("Startup failed: %s", exc)
        return 1

    bot.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
