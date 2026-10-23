"""MQTT 适配器。

覆盖绝大多数 IoT 设备：ESP32、涂鸦、Home Assistant、工业传感器网关……
复用业界标准库 paho-mqtt（零重写），自带后台网络线程，不阻塞 MCP 主循环。

设备配置示例（devices.yaml）：
  - id: living_room_sensor
    protocol: mqtt
    state_topic: home/livingroom/sensor
    command_topic: home/livingroom/actuator/set
    qos: 1
"""

from __future__ import annotations

import json
import time
from typing import Any

import paho.mqtt.client as mqtt

from .base import BaseAdapter, DeviceState


class MqttAdapter(BaseAdapter):
    protocol = "mqtt"

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)
        broker = config.get("broker", {})
        self.host: str = broker.get("host", "localhost")
        self.port: int = int(broker.get("port", 1883))
        self.username: str | None = broker.get("username")
        self.password: str | None = broker.get("password")
        self.client_id: str = broker.get("client_id", f"shb-{name}")

        # 设备 -> 主题映射
        self._devices: dict[str, dict[str, Any]] = {}
        for dev in config.get("devices", []):
            self._devices[dev["id"]] = dev

        self._client: mqtt.Client | None = None
        self._online_since: dict[str, float] = {}

    # ---- 生命周期 ----------------------------------------------------------
    def connect(self) -> None:
        if self._client is not None:
            return
        client = mqtt.Client(client_id=self.client_id, clean_session=True)
        if self.username:
            client.username_pw_set(self.username, self.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        try:
            client.connect(self.host, self.port, keepalive=60)
            client.loop_start()
            self._client = client
        except Exception as exc:  # noqa: BLE001
            raise ConnectionError(f"MQTT 连接失败 {self.host}:{self.port} -> {exc}") from exc

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    # ---- 回调 --------------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc, *args):
        for dev in self._devices.values():
            topic = dev.get("state_topic")
            if topic:
                client.subscribe(topic, qos=int(dev.get("qos", 0)))

    def _on_disconnect(self, client, userdata, rc, *args):
        # 由 paho 自动重连（loop_start 默认行为）
        pass

    def _on_message(self, client, userdata, msg):
        payload = msg.payload
        try:
            data = json.loads(payload.decode("utf-8", "ignore"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {"raw": payload.decode("utf-8", "ignore")}
        # 反查 topic 属于哪个设备
        device_id = self._topic_to_device(msg.topic)
        if device_id:
            self._set_state(device_id, online=True, data=data, ts=time.time())
            self._online_since[device_id] = time.time()

    def _topic_to_device(self, topic: str) -> str | None:
        for dev in self._devices.values():
            if dev.get("state_topic") == topic:
                return dev["id"]
        return None

    # ---- 核心能力 ----------------------------------------------------------
    def discover(self) -> list[str]:
        return list(self._devices.keys())

    def read_state(self, device_id: str) -> DeviceState:
        if device_id not in self._devices:
            return DeviceState(device_id=device_id, online=False, data={"error": "未知设备"})
        cached = self._get_state(device_id)
        if cached is None:
            return DeviceState(device_id=device_id, online=False, data={"error": "暂无数据，未收到上报"})
        # 超过 5 分钟没心跳视为离线
        if cached.updated_at and (time.time() - cached.updated_at) > 300:
            cached.online = False
        return cached

    def send_command(self, device_id: str, command: str, params: dict[str, Any]) -> dict[str, Any]:
        dev = self._devices.get(device_id)
        if not dev:
            return {"ok": False, "error": "未知设备"}
        topic = dev.get("command_topic")
        if not topic:
            return {"ok": False, "error": "该设备未配置 command_topic，无法下发"}
        if self._client is None:
            return {"ok": False, "error": "MQTT 未连接，无法下发指令"}
        payload = {"command": command, "params": params, "ts": time.time()}
        info = self._client.publish(topic, json.dumps(payload), qos=int(dev.get("qos", 0)))
        return {"ok": info.rc == mqtt.MQTT_ERR_SUCCESS, "topic": topic, "payload": payload}
