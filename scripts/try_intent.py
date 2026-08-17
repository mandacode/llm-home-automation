#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
import time

from jarvis.config import load_config
from jarvis.core.pipeline import Pipeline
from jarvis.devices.registry import DeviceRegistry
from jarvis.devices.shelly import ShellyGen3Adapter
from jarvis.llm.openai_compat import OpenAICompatParser

CASES = [
    "włącz pączka",
    "zgaś pączek",
    "sprawdź ile bierze prądu pączek",
    "a co tam u pączka, świeci?",
    "włącz lampę w garażu",
    "otwórz bramę wjazdową",
    "jaka jutro pogoda?",
]


async def main() -> int:
    config = load_config()
    registry = DeviceRegistry.from_yaml(config.devices_config)
    parser = OpenAICompatParser(
        registry=registry,
        api_key=config.llm_api_key,
        model=config.llm_model,
        base_url=config.llm_base_url,
        use_structured_output=config.uses_structured_output,
        max_tokens=config.llm_max_tokens,
        reasoning_effort=config.llm_reasoning_effort,
    )
    pipeline = Pipeline(
        transcriber=None,
        parser=parser,
        registry=registry,
        adapters={ShellyGen3Adapter.device_type: ShellyGen3Adapter(config.device_timeout_s)},
    )

    cases = sys.argv[1:] or CASES
    total = 0.0
    for text in cases:
        started = time.perf_counter()
        result = await pipeline.handle_text(text)
        elapsed = time.perf_counter() - started
        total += elapsed
        print(f'\n„{text}"\n  [{elapsed:.2f}s] {result.message.splitlines()[0]}')

    print(f"\n{'=' * 55}\naverage latency: {total / len(cases):.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
