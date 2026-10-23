# 智能硬件接入 WorkBuddy · MCP 桥接服务器

> 让 WorkBuddy（及任意 MCP 客户端）用自然语言控制真实世界的设备：
> **"客厅现在几度？"** → 读状态 ｜ **"把办公室插座关掉"** → 下发指令。

作者：**晨星** ｜ License：MIT ｜ 状态：可运行 MVP（冒烟测试全绿）

---

## 一、它解决什么

智能硬件（ESP32、涂鸦、Home Assistant、工业 PLC、智能插座、摄像头…）各自一套协议，
AI 助手碰不到。本项目提供一个**统一桥接层**：

```
自然语言 ──> WorkBuddy ──> MCP ──> 本桥接服务器 ──> MQTT / HTTP / (可扩展)
                                                    │
                                                    └─> 真实设备 / 工厂 / 家居
```

- **零重写**：复用业界最成熟库（paho-mqtt、requests、官方 MCP SDK），不自造轮子。
- **可扩展**：新增一种协议 = 写一个 `BaseAdapter` 子类，服务器代码一行不动。
- **可卖**：开源核心引流，上层做托管 / 付费适配器 / 定制咨询。

---

## 二、支持的协议（开箱即用）

| 协议   | 覆盖场景                              | 适配器 | 状态 |
|--------|---------------------------------------|--------|------|
| MQTT   | ESP32 / 涂鸦 / HA / 工业传感器网关    | `MqttAdapter` | ✅ |
| HTTP   | 智能插座 / 摄像头 / 私有云 API        | `HttpAdapter` | ✅ |
| Modbus | 工业 PLC（规划中）                    | —      | ⏳ |
| BLE    | 蓝牙 Arduino / 手环（规划中）         | —      | ⏳ |

---

## 三、快速开始

```bash
# 1. 装依赖（已验证 Python 3.13）
pip install -r requirements.txt

# 2. 准备配置：复制示例，填入你的设备
cp config/devices.example.yaml config/devices.yaml

# 3. 启动 MCP 服务器（stdio，供 WorkBuddy 调用）
python -m src.server
# 或开发模式（自带 Inspector）：
mcp dev src/server.py
```

冒烟测试（无需真实硬件，验证注册表 + 工具）：

```bash
python verify.py
```

---

## 四、💰 赚钱模型（核心）

白皮书我读不到，但"智能硬件 + AI 助手"本身就是蓝海。变现路径分四层，**开源核心是漏斗入口**：

| 层级 | 产品 | 收费方式 | 毛利 | 谁买单 |
|------|------|----------|------|--------|
| L0 | **开源桥接核心**（本仓库） | 免费 · GitHub 署名晨星 | — | 引流 / 建立技术权威 |
| L1 | **托管云桥 SaaS** | 订阅 ¥29–99/月 | 高 | 不想自己部署的小白 / 小微企业 |
| L2 | **品牌付费适配器** | 单次 ¥99–499/品牌 | 极高 | 用涂鸦/小米/某 PLC 的开发者 |
| L3 | **定制集成咨询** | 项目制 ¥5k–50k | 最高 | 工厂 / 园区 / 连锁店 |

**落地顺序建议：**
1. 现在就把本仓库推到 GitHub（署名晨星），写清楚"让 AI 控制你的硬件"。
2. 叠一个 `docker-compose` + 一键托管脚本 → 卖 L1 订阅（零边际成本）。
3. 按品牌做 premium 适配器（封装各家私有协议）→ 卖 L2。
4. 接定制项目 → 卖 L3，反哺开源。

> 关键判断：硬件协议是**碎片化护城河**——谁把最多设备"翻译"成 AI 能懂的语言，
> 谁就握住入口。开源建信任，闭源/服务收钱。

---

## 五、接入 WorkBuddy

在 `~/.workbuddy/mcp.json` 的 `mcpServers` 中加一项（合并，勿覆盖其它）：

```json
{
  "mcpServers": {
    "smart-hardware-bridge": {
      "command": "C:/Users/Administrator/.workbuddy/binaries/python/envs/shb/Scripts/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:/Users/Administrator/WorkBuddy/2026-10-23-23-51-43/smart-hardware-bridge",
      "env": { "SHB_CONFIG": "config/devices.yaml" }
    }
  }
}
```

保存后在 WorkBuddy 连接器页面对该服务器点 **信任** 即可启用。
之后直接在对话里说"列出我的设备""关掉办公室插座"就能控硬件。

---

## 六、扩展新协议

1. 在 `src/adapters/` 新建 `xxx_adapter.py`，继承 `BaseAdapter`，实现
   `connect / disconnect / discover / read_state / send_command`。
2. 在 `src/registry.py` 的 `ADAPTER_FACTORY` 登记一行：`"xxx": XxxAdapter`。
3. 在 `devices.yaml` 用 `protocol: xxx` 写设备。完成，服务器无需改动。

---

## 七、目录结构

```
smart-hardware-bridge/
├── src/
│   ├── server.py            # FastMCP 服务器，暴露 4 个工具
│   ├── registry.py          # 配置加载 + 按协议路由
│   └── adapters/
│       ├── base.py          # 适配器抽象基类
│       ├── mqtt_adapter.py  # MQTT（ESP32/涂鸦/HA/工业）
│       └── http_adapter.py  # HTTP/REST（插座/摄像头/云）
├── config/
│   ├── devices.example.yaml # 配置示例
│   └── devices.yaml         # 你的真实配置（已 gitignore）
├── requirements.txt
├── verify.py                # 冒烟测试
├── LICENSE                  # MIT · 晨星
└── README.md
```

---

© 2026 晨星 (MorningStar) — 世界顶级 AI 锻造计划 · 集大成 / 零重写 / 闭环交付
