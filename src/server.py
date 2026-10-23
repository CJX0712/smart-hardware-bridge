"""智能硬件 MCP 桥接服务器（FastMCP）。

让 WorkBuddy / 任意 MCP 客户端用自然语言控制真实世界的设备：
  "客厅传感器现在几度？"  -> read_device_state
  "把办公室插座关掉"      -> send_device_command

启动：python -m src.server   或   mcp dev src/server.py
配置：环境变量 SHB_CONFIG 指向 devices.yaml，默认读 config/devices.yaml
"""

from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from .adapters.base import BaseAdapter
from .registry import DeviceRegistry

mcp = FastMCP("smart-hardware-bridge")

# 全局注册表（进程级单例）
_REGISTRY = DeviceRegistry()
_REGISTRY.load()
_REGISTRY.connect_all()


def _ok(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def list_devices() -> str:
    """列出桥接器已接入的全部设备（ID / 协议 / 所属适配器）。"""
    return _ok({"count": len(_REGISTRY.list_devices()), "devices": _REGISTRY.list_devices()})


@mcp.tool()
def read_device_state(device_id: str) -> str:
    """读取某个设备的实时状态（温度、开关、在线情况等）。"""
    adapter: BaseAdapter | None = _REGISTRY.resolve(device_id)
    if adapter is None:
        return _ok({"error": f"未找到设备 {device_id}"})
    return _ok(adapter.read_state(device_id).to_dict())


@mcp.tool()
def send_device_command(device_id: str, command: str, params_json: str = "{}") -> str:
    """向设备下发指令。command 如 on/off/set_temp，params_json 传额外参数。"""
    adapter: BaseAdapter | None = _REGISTRY.resolve(device_id)
    if adapter is None:
        return _ok({"error": f"未找到设备 {device_id}"})
    params = BaseAdapter._parse_params(params_json)
    return _ok(adapter.send_command(device_id, command, params))


@mcp.tool()
def bridge_status() -> str:
    """查看桥接服务器与各适配器的健康状态。"""
    return _ok({
        "adapters": [
            {"name": a.name, "protocol": a.protocol, "devices": a.discover()}
            for a in _REGISTRY.adapters
        ],
        "total_devices": len(_REGISTRY.list_devices()),
    })


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        _REGISTRY.disconnect_all()
