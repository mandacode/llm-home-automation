from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": None,
    "ollama": None,
}


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Config:
    telegram_token: str
    allowed_user_ids: frozenset[int]

    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str | None
    llm_max_tokens: int
    llm_reasoning_effort: str | None

    stt_provider: str
    stt_model: str
    stt_api_key: str
    stt_base_url: str | None
    stt_language: str

    devices_config: str
    device_timeout_s: float

    @property
    def uses_structured_output(self) -> bool:
        return self.llm_provider in ("groq", "openai")


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    for base in (Path.cwd(), PROJECT_ROOT):
        candidate = base / path
        if candidate.exists():
            return candidate
    return Path.cwd() / path


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _parse_user_ids(raw: str) -> frozenset[int]:
    ids = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError as exc:
            raise ConfigError(f"TELEGRAM_ALLOWED_USER_IDS: {chunk!r} is not a number.") from exc
    return frozenset(ids)


def load_config() -> Config:
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(PROJECT_ROOT / ".env")

    llm_provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    stt_provider = os.getenv("STT_PROVIDER", "groq").strip().lower()

    if llm_provider == "ollama":
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        llm_base_url = f"{ollama_host}/v1"
        llm_api_key = "ollama"
        llm_model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b-instruct")
    else:
        llm_base_url = BASE_URLS.get(llm_provider)
        llm_api_key = _require("GROQ_API_KEY" if llm_provider == "groq" else "OPENAI_API_KEY")
        llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

    stt_api_key = _require("GROQ_API_KEY" if stt_provider == "groq" else "OPENAI_API_KEY")

    return Config(
        telegram_token=_require("TELEGRAM_BOT_TOKEN"),
        allowed_user_ids=_parse_user_ids(os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")),
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
        llm_reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "low").strip() or None,
        stt_provider=stt_provider,
        stt_model=os.getenv("STT_MODEL", "whisper-large-v3-turbo"),
        stt_api_key=stt_api_key,
        stt_base_url=BASE_URLS.get(stt_provider),
        stt_language=os.getenv("STT_LANGUAGE", "pl"),
        devices_config=str(_resolve_path(os.getenv("DEVICES_CONFIG", "config/devices.yaml"))),
        device_timeout_s=float(os.getenv("DEVICE_TIMEOUT_S", "4.0")),
    )
