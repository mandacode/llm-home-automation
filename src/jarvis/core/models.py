from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    TOGGLE = "toggle"
    STATUS = "status"
    UNKNOWN = "unknown"

    @property
    def is_actionable(self) -> bool:
        return self is not Action.UNKNOWN


@dataclass(frozen=True, slots=True)
class Device:
    id: str
    name: str
    type: str
    host: str
    room: str | None = None
    aliases: tuple[str, ...] = ()

    def describe_for_prompt(self) -> str:
        parts = [f"{self.id}: {self.name}"]
        if self.room:
            parts.append(f"pokój={self.room}")
        if self.aliases:
            parts.append("mówi się też: " + ", ".join(self.aliases))
        return " | ".join(parts)


@dataclass(frozen=True, slots=True)
class Intent:
    action: Action
    device_id: str | None
    is_device_command: bool = True
    raw_text: str = ""


@dataclass(frozen=True, slots=True)
class ActionResult:
    ok: bool
    message: str
    device: Device | None = None

    @classmethod
    def failure(cls, message: str) -> ActionResult:
        return cls(ok=False, message=message)

    @classmethod
    def success(cls, message: str, device: Device | None = None) -> ActionResult:
        return cls(ok=True, message=message, device=device)
