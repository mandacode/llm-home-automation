from __future__ import annotations

from pathlib import Path

import yaml

from ..core.models import Device


class DeviceRegistryError(RuntimeError):
    pass


class DeviceRegistry:
    def __init__(self, devices: list[Device]) -> None:
        if not devices:
            raise DeviceRegistryError("Device registry is empty — nothing to control.")

        seen: dict[str, Device] = {}
        for device in devices:
            if device.id in seen:
                raise DeviceRegistryError(f"Duplicate device id: {device.id!r}")
            seen[device.id] = device

        self._by_id = seen

    @classmethod
    def from_yaml(cls, path: str | Path) -> DeviceRegistry:
        config_path = Path(path)
        if not config_path.is_file():
            raise DeviceRegistryError(
                f"Registry file not found: {config_path}. "
                "Copy config/devices.example.yaml and fill in the IP addresses."
            )

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        entries = raw.get("devices")
        if not isinstance(entries, list):
            raise DeviceRegistryError(f"{config_path}: expected a list under key 'devices'.")

        return cls([cls._parse_entry(entry, i, config_path) for i, entry in enumerate(entries)])

    @staticmethod
    def _parse_entry(entry: object, index: int, path: Path) -> Device:
        if not isinstance(entry, dict):
            raise DeviceRegistryError(f"{path}: entry #{index} is not a mapping.")

        missing = [key for key in ("id", "name", "type", "host") if not entry.get(key)]
        if missing:
            raise DeviceRegistryError(
                f"{path}: entry #{index} is missing required fields: {', '.join(missing)}"
            )

        aliases = entry.get("aliases") or []
        if not isinstance(aliases, list):
            raise DeviceRegistryError(f"{path}: 'aliases' in entry #{index} must be a list.")

        misheard = entry.get("misheard") or []
        if not isinstance(misheard, list):
            raise DeviceRegistryError(f"{path}: 'misheard' in entry #{index} must be a list.")

        return Device(
            id=str(entry["id"]),
            name=str(entry["name"]),
            type=str(entry["type"]),
            host=str(entry["host"]),
            room=str(entry["room"]) if entry.get("room") else None,
            aliases=tuple(str(alias) for alias in aliases),
            misheard=tuple(str(term) for term in misheard),
        )

    def ids(self) -> list[str]:
        return list(self._by_id)

    def all(self) -> list[Device]:
        return list(self._by_id.values())

    def resolve(self, device_id: str | None) -> Device | None:
        if not device_id:
            return None
        return self._by_id.get(device_id)

    def describe_for_prompt(self) -> str:
        return "\n".join(f"- {device.describe_for_prompt()}" for device in self.all())

    def vocabulary_hint(self) -> str:
        terms: list[str] = []
        for device in self.all():
            terms.append(device.name)
            terms.extend(device.aliases)
        unique = list(dict.fromkeys(terms))
        return ", ".join(unique) + "."

    def __len__(self) -> int:
        return len(self._by_id)
