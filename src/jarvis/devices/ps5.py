from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import Any

from ..core.models import Device
from .base import DeviceError

DDP_PORT = 9302
DDP_VERSION = "00030010"
STATUS_ON = 200
STATUS_STANDBY = 620


def _ddp_status(host: str, timeout: float) -> dict[str, str]:
    payload = f"SRCH * HTTP/1.1\ndevice-discovery-protocol-version:{DDP_VERSION}\n".encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(payload, (host, DDP_PORT))
        data, _ = sock.recvfrom(2048)
    except (socket.timeout, OSError):
        return {}
    finally:
        sock.close()

    lines = data.decode(errors="replace").strip().splitlines()
    if not lines:
        return {}
    result: dict[str, str] = {}
    first = lines[0].split(None, 1)
    result["status-code"] = first[1].split()[0] if len(first) > 1 else ""
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


class PS5Adapter:
    device_type = "ps5"

    def __init__(
        self,
        profile_path: str | Path,
        probe_timeout_s: float = 4.0,
        transition_timeout_s: float = 30.0,
    ) -> None:
        self._profile_path = Path(profile_path).expanduser()
        self._probe_timeout = probe_timeout_s
        self._transition_timeout = transition_timeout_s

    def _credentials(self, device: Device) -> tuple[str, str, str]:
        if not self._profile_path.is_file():
            raise DeviceError(
                f"{device.name}: brak pliku rejestracji ({self._profile_path}). "
                "Uruchom kreator: pyremoteplay -r <ip>"
            )
        try:
            profiles = json.loads(self._profile_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise DeviceError(f"{device.name}: uszkodzony plik rejestracji.") from exc

        wanted = device.options.get("host_id")
        for user, data in profiles.items():
            for host_id, host in (data.get("hosts") or {}).items():
                if wanted and host_id != wanted:
                    continue
                key = (host.get("data") or {}).get("RegistKey")
                if key:
                    return user, host_id, key

        raise DeviceError(
            f"{device.name}: konsola nie jest zarejestrowana. Uruchom: pyremoteplay -r {device.host}"
        )

    async def _status_code(self, device: Device) -> int | None:
        status = await asyncio.to_thread(_ddp_status, device.host, self._probe_timeout)
        raw = status.get("status-code")
        return int(raw) if raw and raw.isdigit() else None

    async def _wait_for(self, device: Device, target: int) -> bool:
        deadline = asyncio.get_running_loop().time() + self._transition_timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(3)
            if await self._status_code(device) == target:
                return True
        return False

    def _wake_blocking(self, device: Device, key: str) -> None:
        import warnings

        warnings.filterwarnings("ignore")
        from pyremoteplay import RPDevice

        rp = RPDevice(device.host)
        rp.get_status()
        # Wybudzanie przez `user=` zawodzi: w trybie spoczynku konsola nie zwraca host-id,
        # wiec biblioteka nie dopasowuje profilu. Klucz rejestracyjny ma pierwszenstwo.
        rp.wakeup(key=key)

    def _standby_blocking(self, device: Device, user: str) -> None:
        import warnings

        warnings.filterwarnings("ignore")
        from pyremoteplay import RPDevice

        rp = RPDevice(device.host)
        rp.get_status()
        profiles = RPDevice.get_profiles(str(self._profile_path))
        result = rp.standby(user, profiles)
        if asyncio.iscoroutine(result):
            asyncio.run(result)

    async def turn_on(self, device: Device) -> str:
        if await self._status_code(device) == STATUS_ON:
            return f"ℹ️ {device.name} już działa"

        _, _, key = self._credentials(device)
        await asyncio.to_thread(self._wake_blocking, device, key)

        if await self._wait_for(device, STATUS_ON):
            return f"✅ {device.name} — włączone"
        raise DeviceError(
            f"{device.name}: wysłałem sygnał, ale konsola nie wstała w "
            f"{self._transition_timeout:.0f}s. Sprawdź, czy jest w trybie spoczynku, "
            "a nie wyłączona całkowicie."
        )

    async def turn_off(self, device: Device) -> str:
        code = await self._status_code(device)
        if code == STATUS_STANDBY:
            return f"ℹ️ {device.name} już jest w trybie spoczynku"
        if code is None:
            raise DeviceError(f"{device.name} nie odpowiada — sprawdź zasilanie i sieć.")

        user, _, _ = self._credentials(device)
        await asyncio.to_thread(self._standby_blocking, device, user)

        # standby() potrafi zglosic porazke mimo powodzenia — ufamy tylko realnemu statusowi.
        if await self._wait_for(device, STATUS_STANDBY):
            return f"✅ {device.name} — tryb spoczynku"
        raise DeviceError(f"{device.name}: nie przeszła w tryb spoczynku.")

    async def toggle(self, device: Device) -> str:
        code = await self._status_code(device)
        if code == STATUS_ON:
            return await self.turn_off(device)
        return await self.turn_on(device)

    async def status(self, device: Device) -> str:
        info: dict[str, Any] = await asyncio.to_thread(
            _ddp_status, device.host, self._probe_timeout
        )
        raw = info.get("status-code")
        code = int(raw) if raw and raw.isdigit() else None

        if code == STATUS_ON:
            line = f"ℹ️ {device.name} — włączone"
            app = info.get("running-app-name")
            if app:
                line += f", uruchomione: {app}"
            return line
        if code == STATUS_STANDBY:
            return f"ℹ️ {device.name} — tryb spoczynku"
        raise DeviceError(f"{device.name} nie odpowiada — sprawdź zasilanie i sieć.")
