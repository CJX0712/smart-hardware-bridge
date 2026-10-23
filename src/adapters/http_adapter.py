"""HTTP / REST 适配器。

覆盖走 Web API 的硬件：智能插座（Sonoff）、摄像头、网关、私有云平台……
复用 requests（零重写），同步调用由 MCP 执行器在后台线程跑，不阻塞事件循环。

设备配置示例：
  - id: office_plug
    protocol: http
    base_url: http://192.168.1.50
    state_path: /api/v1/state      # GET
    command_path: /api/v1/control  # POST
    timeout: 5
"""

from __future__ import annotations

import time
from typing import Any

import requests

from .base import BaseAdapter, DeviceState


class HttpAdapter(BaseAdapter):
    protocol = "http"

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)
        self._devices: dict[str, dict[str, Any]] = {}
        for dev in config.get("devices", []):
            self._devices[dev["id"]] = dev
        self._timeout: int = int(config.get("timeout", 5))

    def connect(self) -> None:
        # HTTP 是无连接的，connect 仅做连通性自检。
        return

    def disconnect(self) -> None:
        return

    def discover(self) -> list[str]:
        return list(self._devices.keys())

    def read_state(self, device_id: str) -> DeviceState:
        dev = self._devices.get(device_id)
        if not dev:
            return DeviceState(device_id=device_id, online=False, data={"error": "未知设备"})
        url = f"{dev['base_url'].rstrip('/')}{dev.get('state_path', '/')}"
        try:
            resp = requests.get(url, timeout=self._timeout)
            data = resp.json() if resp.content else {}
            self._set_state(device_id, online=resp.ok, data=data, ts=time.time())
            return self._get_state(device_id) or DeviceState(device_id=device_id, online=resp.ok, data=data)
        except Exception as exc:  # noqa: BLE001
            return DeviceState(device_id=device_id, online=False, data={"error": str(exc)})

    def send_command(self, device_id: str, command: str, params: dict[str, Any]) -> dict[str, Any]:
        dev = self._devices.get(device_id)
        if not dev:
            return {"ok": False, "error": "未知设备"}
        path = dev.get("command_path")
        if not path:
            return {"ok": False, "error": "该设备未配置 command_path"}
        url = f"{dev['base_url'].rstrip('/')}{path}"
        body = {"command": command, "params": params, "ts": time.time()}
        try:
            resp = requests.post(url, json=body, timeout=self._timeout)
            return {"ok": resp.ok, "status_code": resp.status_code, "response": resp.text[:500]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
