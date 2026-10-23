"""冒烟测试：验证注册表加载、适配器构建、工具可调用。"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import src.server as srv  # noqa: E402

print("== bridge_status ==")
print(srv.bridge_status())

print("\n== list_devices ==")
print(srv.list_devices())

print("\n== read_device_state(office_plug) [HTTP, 会连不通但应返回结构] ==")
print(srv.read_device_state("office_plug"))

print("\n== send_device_command(living_room_sensor) [MQTT 未连, 应返回结构化错误] ==")
print(srv.send_device_command("living_room_sensor", "on", "{}"))

print("\n== 未知设备 ==")
print(srv.read_device_state("does_not_exist"))

print("\nALL_OK")
