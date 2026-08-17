from __future__ import annotations

from typing import Any

from ..core.models import Action
from ..devices.registry import DeviceRegistry


def build_intent_schema(registry: DeviceRegistry) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "device_id", "is_device_command"],
        "properties": {
            "is_device_command": {
                "type": "boolean",
                "description": (
                    "true, jeśli wypowiedź jest poleceniem dotyczącym jakiegokolwiek urządzenia "
                    "domowego — nawet jeśli tego urządzenia nie ma na liście. "
                    "false dla pytań i rozmowy niezwiązanej z urządzeniami."
                ),
            },
            "action": {
                "type": "string",
                "enum": [action.value for action in Action],
                "description": (
                    "Co zrobić. Użyj 'unknown', gdy wypowiedź nie jest poleceniem "
                    "dotyczącym urządzenia albo gdy nie masz pewności."
                ),
            },
            "device_id": {
                "type": ["string", "null"],
                "enum": [*registry.ids(), None],
                "description": (
                    "Identyfikator urządzenia WYŁĄCZNIE z podanej listy. "
                    "Jeśli żadne nie pasuje, zwróć null — nie wymyślaj wartości."
                ),
            },
        },
    }


def build_response_format(registry: DeviceRegistry) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "home_intent",
            "strict": True,
            "schema": build_intent_schema(registry),
        },
    }
