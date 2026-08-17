from __future__ import annotations

from typing import Any

import httpx

from ..core.models import Device
from .base import DeviceError

SWITCH_ID = 0


class ShellyGen3Adapter:
    device_type = "shelly_plug"

    def __init__(self, timeout_s: float = 4.0) -> None:
        self._timeout = timeout_s

    async def _rpc(self, device: Device, method: str, **params: Any) -> dict[str, Any]:
        url = f"http://{device.host}/rpc/{method}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise DeviceError(
                f"{device.name} nie odpowiada (timeout {self._timeout}s). "
                "Sprawdź, czy jest zasilane i czy ma ten adres IP."
            ) from exc
        except httpx.HTTPError as exc:
            raise DeviceError(f"{device.name}: błąd komunikacji ({exc}).") from exc
        except ValueError as exc:
            raise DeviceError(f"{device.name}: niezrozumiała odpowiedź urządzenia.") from exc

    async def turn_on(self, device: Device) -> str:
        await self._rpc(device, "Switch.Set", id=SWITCH_ID, on="true")
        return f"✅ {device.name} — włączone"

    async def turn_off(self, device: Device) -> str:
        await self._rpc(device, "Switch.Set", id=SWITCH_ID, on="false")
        return f"✅ {device.name} — wyłączone"

    async def toggle(self, device: Device) -> str:
        result = await self._rpc(device, "Switch.Toggle", id=SWITCH_ID)
        now_on = not bool(result.get("was_on", False))
        return f"✅ {device.name} — {'włączone' if now_on else 'wyłączone'}"

    async def status(self, device: Device) -> str:
        result = await self._rpc(device, "Switch.GetStatus", id=SWITCH_ID)
        state = "włączone" if result.get("output") else "wyłączone"

        line = f"ℹ️ {device.name} — {state}"

        power = result.get("apower")
        if isinstance(power, (int, float)):
            line += f", pobór {power:.1f} W"

        return line

    async def identify(self, device: Device) -> dict[str, Any]:
        return await self._rpc(device, "Shelly.GetDeviceInfo")
