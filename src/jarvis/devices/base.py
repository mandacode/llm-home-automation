from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..core.models import Device


class DeviceError(RuntimeError):
    pass


@runtime_checkable
class DeviceAdapter(Protocol):
    device_type: str

    async def turn_on(self, device: Device) -> str: ...

    async def turn_off(self, device: Device) -> str: ...

    async def toggle(self, device: Device) -> str: ...

    async def status(self, device: Device) -> str: ...
