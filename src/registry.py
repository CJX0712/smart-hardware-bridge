"""设备注册表：加载配置、按协议构建适配器、统一路由。"""

from __future__ import annotations

import os
from typing import Any

import yaml

from .adapters.base import BaseAdapter
from .adapters.http_adapter import HttpAdapter
from .adapters.mqtt_adapter import MqttAdapter

# 协议名 -> 适配器类（新增协议在此登记一行即可）
ADAPTER_FACTORY: dict[str, type[BaseAdapter]] = {
    MqttAdapter.protocol: MqttAdapter,
    HttpAdapter.protocol: HttpAdapter,
}

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "devices.yaml")


class DeviceRegistry:
    """持有所有适配器，并按 device_id 路由到正确的适配器。"""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or os.environ.get("SHB_CONFIG", DEFAULT_CONFIG)
        self.adapters: list[BaseAdapter] = []
        self._device_to_adapter: dict[str, BaseAdapter] = {}

    def load(self) -> None:
        if not os.path.exists(self.config_path):
            print(f"[warn] 配置文件不存在: {self.config_path}，将以空注册表启动。复制 config/devices.example.yaml 为 devices.yaml 后重启即可接入设备。")
            self.adapters = []
            self._device_to_adapter = {}
            return
        with open(self.config_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        self.adapters = []
        self._device_to_adapter = {}
        for entry in cfg.get("adapters", []):
            proto = entry.get("protocol", "base")
            cls = ADAPTER_FACTORY.get(proto)
            if cls is None:
                # 未知协议：跳过并提示，不崩
                print(f"[warn] 未知协议 {proto}，已跳过适配器 {entry.get('name')}")
                continue
            adapter = cls(entry.get("name", proto), entry)
            for dev_id in (d.get("id") for d in entry.get("devices", [])):
                self._device_to_adapter[dev_id] = adapter
            self.adapters.append(adapter)

    def connect_all(self) -> None:
        for adapter in self.adapters:
            try:
                adapter.connect()
            except Exception as exc:  # noqa: BLE001
                print(f"[error] 适配器 {adapter.name} 连接失败: {exc}")

    def disconnect_all(self) -> None:
        for adapter in self.adapters:
            try:
                adapter.disconnect()
            except Exception:  # noqa: BLE001
                pass

    def resolve(self, device_id: str) -> BaseAdapter | None:
        return self._device_to_adapter.get(device_id)

    def list_devices(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for adapter in self.adapters:
            for device_id in adapter.discover():
                out.append({
                    "device_id": device_id,
                    "protocol": adapter.protocol,
                    "adapter": adapter.name,
                })
        return out
