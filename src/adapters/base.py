"""智能硬件适配器基类。

所有协议适配器（MQTT / HTTP / Modbus / BLE …）都继承 BaseAdapter，
对外暴露统一的 发现 / 读状态 / 下发指令 三件套。
新增一种硬件协议 = 写一个子类，零改服务器代码。
"""

from __future__ import annotations

import abc
import json
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceState:
    """设备状态的统一容器。"""

    device_id: str
    online: bool = False
    data: dict[str, Any] = field(default_factory=dict)
    updated_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "online": self.online,
            "data": self.data,
            "updated_at": self.updated_at,
        }


class BaseAdapter(abc.ABC):
    """协议适配器抽象基类。

    设计原则（集大成 / 零重写）：
    - 复用业界最成熟的客户端库（paho-mqtt、requests …），不自造轮子。
    - 服务器只依赖本基类接口，协议细节完全隔离在子类里。
    """

    #: 子类必须声明自己支持的协议名（配置里靠它路由）。
    protocol: str = "base"

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self._lock = threading.RLock()
        self._states: dict[str, DeviceState] = {}

    # ---- 生命周期 ----------------------------------------------------------
    @abc.abstractmethod
    def connect(self) -> None:
        """建立到broker / 网关 / 设备的连接。"""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """断开连接、释放资源。"""

    # ---- 核心能力（子类按需实现，默认抛 NotImplemented）-------------------
    @abc.abstractmethod
    def discover(self) -> list[str]:
        """返回本适配器能看到的设备 ID 列表。"""

    @abc.abstractmethod
    def read_state(self, device_id: str) -> DeviceState:
        """读取单个设备的最新状态。"""

    @abc.abstractmethod
    def send_command(self, device_id: str, command: str, params: dict[str, Any]) -> dict[str, Any]:
        """向设备下发一条指令，返回执行结果。"""

    # ---- 公共工具 ----------------------------------------------------------
    def _set_state(self, device_id: str, online: bool, data: dict[str, Any], ts: float) -> None:
        import time

        with self._lock:
            self._states[device_id] = DeviceState(
                device_id=device_id,
                online=online,
                data=data,
                updated_at=ts if ts is not None else time.time(),
            )

    def _get_state(self, device_id: str) -> DeviceState | None:
        with self._lock:
            return self._states.get(device_id)

    def snapshot(self) -> dict[str, Any]:
        """导出全部缓存状态（供调试 / 资源暴露）。"""
        with self._lock:
            return {did: st.to_dict() for did, st in self._states.items()}

    @staticmethod
    def _parse_params(params: str | dict | None) -> dict[str, Any]:
        if not params:
            return {}
        if isinstance(params, dict):
            return params
        try:
            return json.loads(params)
        except (json.JSONDecodeError, TypeError):
            return {}
