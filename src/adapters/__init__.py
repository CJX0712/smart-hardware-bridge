"""协议适配器包。新增协议：在此目录加一个 adapter 子类并到 registry 登记。"""

from .base import BaseAdapter, DeviceState
from .http_adapter import HttpAdapter
from .mqtt_adapter import MqttAdapter

__all__ = ["BaseAdapter", "DeviceState", "HttpAdapter", "MqttAdapter"]
