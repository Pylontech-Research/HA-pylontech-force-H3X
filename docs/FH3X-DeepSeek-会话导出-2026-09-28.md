# FH3X Home Assistant 会话导出

导出日期：2026-09-28  
用途：提供给 DeepSeek 继续分析、接手开发和复核项目。

## 导出说明

本文档根据当前会话中可见的用户需求、开发结论、代码变更、测试结果和交接资料整理。平台没有提供原始会话数据库导出接口，因此不能保证包含所有历史助手原文；重复的“继续”“在不”等无新增技术信息的消息按阶段归并。涉及密码、Token、完整私有凭据的内容已省略。

## 一、项目背景

- 项目：Pylontech Force H3X 户用储能系统的 Home Assistant 本地集成。
- Home Assistant 设备：Home Assistant Green。
- 通信：Modbus TCP，端口 `502`。
- PCS Modbus 地址：`2`。
- BMS Modbus 地址：`1`。
- 主要目标：通过 HACS 发布自定义集成，提供能源、电池、电网、光伏、控制、告警和诊断实体。
- 暂不包含：云账号、站点管理、蓝牙配网、OTA、自定义 FH3X 前端面板和 Home Assistant Core 上游发布。
- 当前仓库：`/home/kubo/home_assistant`。
- 当前开发分支：`fh3x/shared-library`。
- 集成域：`pylontech_fh3x`。
- 当前 manifest 版本：`0.6.26`。

## 二、对话阶段和关键需求

### 1. Home Assistant Green 首次联网

用户遇到的问题：

- iPhone 扫描不到 Home Assistant。
- `homeassistant.local:8123` 无法访问。
- Green 与电脑/手机存在不同网段、VirtualBox NAT、Wi-Fi 和以太网共享等情况。
- Green 初次安装长时间停在 Supervisor 镜像下载。

确认结论：

- Green 需要以太网才能首次联网，iPhone 自动发现依赖 mDNS/Bonjour。
- `homeassistant.local` 失败而 IP 可访问，主要是 NAT、VLAN、访客网络、客户端隔离或 mDNS 不转发。
- Green 曾使用过 `172.22.184.161`、`172.22.194.35` 等地址，地址变化与 DHCP/Wi-Fi 切换有关。
- `/dev/fb0` 日志是正常的显示帧缓冲硬件检测，不是卡死原因。
- `ghcr.io` 镜像下载慢通常与 DNS、代理或网络出口有关。
- Observer 地址用于查看 Supervisor 健康状态，不是普通 HA 页面。
- Green 的 HDMI 主要用于调试/控制台显示，不等于完整的视频播放设备。

### 2. 代理和 SSH/Samba

用户配置过电脑 Clash 代理，把 Green 接到电脑以太网共享网络；代理端口曾使用 `7897`。

结论：

- HA 中配置代理时应使用电脑在共享网络中的局域网 IP 和代理端口。
- SSH 使用 Green 当前可达 IP、端口 `2222`、root 用户；凭据不写入本导出文件。
- Samba、SSH 可用于部署自定义集成，但部署前必须备份 `/config/custom_components`。
- SSH add-on 的 shell 不等于宿主机 shell，通常看不到宿主机 Docker 命令。

### 3. FH3X 集成初始开发

用户提供了 Pylontech Force H3X 社区项目链接，并要求：

- 参考 `HA-pylontech-force-H3X` 项目。
- 把社区项目优势并入现有集成。
- 暂时只做本地 Modbus，不做账号、站点、OTA、云端和蓝牙配网。
- 支持 Modbus Slave 模拟器进行开发。
- 完整覆盖 App 需要的点位，但默认页面不能展示过多工程参数。

已形成的架构：

```text
Config Flow / Options
        |
        v
FH3XModbusClient  -- Modbus TCP --> PCS(ID 2) / BMS(ID 1)
        |
        v
FH3XCoordinator
        |
        +--> protocol.py --> Sensor / Binary Sensor / Number / Select / Switch / Time
        +--> AlarmEventTracker --> Recorder / Logbook
        +--> diagnostics.py --> 脱敏诊断下载
```

关键约束：

- 保留实体唯一 ID、配置项唯一 ID、PCS/BMS 地址和旧用户配置。
- 通信超时不能被解释为告警恢复、零功率、零累计电量或设备主动断网。
- 写入必须串行化，写入后读回校验，再刷新实体。
- 不暴露未经协议或真机验证的写入寄存器。

### 4. 前端、Figma 和 Tesla 风格讨论

用户曾要求参考 FH3X Figma 和 Tesla Powerwall 的能源交互逻辑，设计动态能量流和商业化页面；随后确认：

- HA 自带 Lovelace，不应额外注册一个容易黑屏的 FH3X 自定义面板。
- 暂时删除/停止 UI 和前端面板方向。
- 优先完成官方 Integration、实体、控制、告警和 HACS 规范。
- Tesla 只作为能源信息层级和交互逻辑参考，不复制 Logo、Powerwall 外形、图标或布局。

当前明确不重新注册实验性 FH3X 前端面板。

### 5. 实体和控制优化

用户要求按普通 HA 用户习惯整理实体：

- Controls：EMS 模式、EPS 输出、计划 1～4 启用。
- Configuration：手动充放电功率、充电上限 SOC、并网/离网 EPS 保留 SOC。
- Advanced：完整计划参数、星期、削峰、热泵和工程限制。
- 不把所有原始点位默认暴露到设备页。
- 中英文显示名应跟随 HA 语言切换。
- “Charge/discharge power reference” 等控制项需要解释当前模式、范围和不可用原因。

控制档位：

| 档位 | Controls | Configuration |
|---|---:|---:|
| Daily controls only | 6 | 0 |
| Daily controls and common settings | 6 | 4 |
| Advanced controls and full schedules | 8 | 51 |

### 6. 能源和累计量问题

重点处理过的问题：

- 能量图把实时 W 错当成累计 Wh/kWh。
- 光伏、电池和电网出现 71 kWh 跳变。
- `home_load_energy` 必须使用 BMS 累计点位，不使用含义不确定的 PCS AC 输出能量回退。
- 单机和并机读取不同 BMS 累计地址。
- `TOTAL_INCREASING` 启动时必须经过连续样本确认，避免 Energy Dashboard 生命周期跳变。
- 临时读取失败保留最后有效值，连续失败达到阈值后才不可用。

家庭负载累计地址规则：

| 场景 | 文档偏移 | 实际地址 |
|---|---:|---:|
| 单机 | `0x0691–0x0692` | `0x1A91–0x1A92` |
| 并机 | `0x06D1–0x06D2` | `0x1AD1–0x1AD2` |

BMS `0x1400` 电池堆区域的表格值是相对偏移，必须加上 `0x1400` 基址；不能把偏移直接当成绝对寄存器地址。

### 7. SSDP 自动发现

FH3X 使用自定义 SSDP 格式，不注册 HA 标准 SSDP 集成。

- 组播：`239.101.1.250:1900`
- 组播源端口：`1901`
- 广播兼容：`255.255.255.255:10088`
- `SERVER` 必须包含 `FH3X`。
- `EXT` 接受 `1` 或 `2`。
- 按 USN 去重；无 USN 时按源 IP 去重。
- 最多发送 3 轮，时间约为 0 秒、3.5 秒、7 秒。
- 收到响应后停止继续发送，但总监听窗口约 15 秒，以收集慢响应的第二台设备。
- 已配置设备不应阻塞第二台设备添加。
- 发现确认页不再强制等待 Modbus 身份验证；设备加载后由正常轮询读取真实身份。
- 永远保留手动 IP 添加入口。

此前出现过的错误：

```text
Config flow could not be loaded:
Handler FH3XConfigFlow doesn't support step discovery_validation_failed
```

已通过增加对应 Config Flow step 修复。

### 8. 告警历史

实时告警实体：

- `inverter_fault`
- `inverter_warning`
- `bms_protection`
- `bms_alarm`

告警历史方案：

- HA Recorder + Logbook。
- `off -> on` 记录触发。
- `on -> off` 记录恢复。
- 告警 bit 发生变化时关闭旧快照并创建新快照。
- 通信超时不记录恢复。
- 未知 bit 显示为 `Unknown alarm bit X`，不显示空白。
- 属性包含 `active_issues`、`active_issue_ids`、原始 bitmask、未知 bit、错误码和时间。
- 不新增独立商业数据库。

### 9. HACS 发布

用户明确选择：

- 当前阶段只准备 HACS 默认商店。
- 不需要此阶段发布到 Home Assistant Core。
- HACS 默认仓库需要稳定目录结构、manifest、README、翻译、版本、测试和 release 流程。
- GitHub topics 已设置为：`home-assistant`、`hacs`、`pylontech`、`modbus`、`energy-storage`、`solar-energy`。
- 不提交密码、Token、备份、私有抓包或协议 DOCX 原文。
- 已有提交历史暂不清理，采用普通提交方式，不强制重写历史。

HACS 发布前的主要未决事项：

- 产品最终实体矩阵仍需确认。
- 所有新增点位需要协议来源、缩放、符号、单位、默认暴露和可用性定义。
- 真机控制验证还需要记录设备型号、固件、拓扑和安全测试范围。
- `fh3x/shared-library` 分支使用独立协议库依赖；HACS 发布前要确定公开依赖来源，或回到嵌入式 `pymodbus` 架构。

## 三、当前代码改动

本轮产品点位适配增加了：

- `custom_components/pylontech_fh3x/product.py`
  - 产品字段别名、缩放、身份、功率上限、第三方 PV 和故障状态归一化。
- `custom_components/pylontech_fh3x/period_stats.py`
  - 日/月统计持久化、累计量基线、重启保护、异常跳变保护。
- `coordinator.py`
  - 轮询后归一化产品字段并更新周期统计。
- `sensor.py`
  - 产品注册表对应的传感器和日/月统计实体。
- `binary_sensor.py`
  - 聚合设备故障和设备告警实体。
- `profiles.py`
  - 产品字段加入暴露档位。
- `protocol.py`
  - 三相数据不完整时不发布错误的平均电压/电流。
- `strings.json`、`translations/en.json`、`translations/zh-Hans.json`
  - 产品点位中英文翻译。
- `docs/FH3X产品点位映射矩阵.md`
  - 产品点位和代码映射说明。

## 四、Green 实体验证记录（2026-09-18）

验证方式：通过 HA 实体 API 读取实际实体状态，不执行写入控制。

在线设备主要状态：

| 实体/数据 | 实测值 |
|---|---:|
| Battery capacity | `5.12 kWh` |
| Home load energy | `3.269 kWh` |
| Home load power | `40–44 W` |
| Battery SOC | `10%` |
| Battery state | `idle` |
| Grid connected | `on` |
| Grid frequency | 约 `50 Hz` |
| Device alarm | `off` |
| Device fault | `off` |
| Current alarm code | `0` |
| PV total energy | `80.396 kWh` |
| Grid import energy | `294.481 kWh` |
| Grid export energy | `194.36 kWh` |

发现并修复的 HA 实体问题：

1. 产品枚举传感器缺少 `ENUM` device class，导致 HA 抛出 `ValueError`。
2. 日/月能量实体声明成 `measurement`，与 `energy` device class 不兼容；已改为 `total`。
3. R 相电压约 `234 V`、S/T 相为 `0` 时，旧逻辑错误显示平均值约 `78 V`；已改为不发布平均值。
4. 三相不完整时平均电流也不再把缺失相当成有效零值。
5. `home_load_energy` 重启后先显示不可用，连续两次有效轮询后恢复 `3.269 kWh`，符合累计量启动保护。

当前第二台配置地址 `172.22.192.198` 存在 Modbus 通信失败，不能把它的 unavailable 直接判断为代码错误，需要先恢复网络或模拟器连接。

Green 上保留了可回滚备份，验证期间只替换了实体/协调器/协议相关文件，保留了 Green 原有 manifest 和 Modbus 依赖架构。

## 五、测试结果

本地执行结果：

```text
python3 -m compileall -q custom_components tests scripts       PASS
python3 -m unittest discover -s tests                          72 tests OK
ruff check custom_components tests scripts                     PASS
ruff format --check custom_components tests scripts             PASS
python3 scripts/validate_repository.py                         PASS
git diff --check                                               PASS
```

测试覆盖：

- PCS/BMS 协议偏移、缩放、符号和无效值。
- 单机/并机累计电量。
- 累计量启动确认、重置和大跳变保护。
- 产品字段和派生功率。
- 三相平均值的完整/缺失/零相场景。
- SSDP 解析、去重、慢响应、多设备和取消清理。
- Config Flow 手动添加、发现、IP 变化和已配置设备。
- 写入串行化、读回和星期位掩码。
- 告警触发、变化、恢复和通信超时。
- 生命周期卸载和连接关闭。

## 六、当前未完成和风险

1. 产品还没有最终确认完整实体矩阵；正式发布前要逐项确认名称、单位、默认暴露、读写权限和协议来源。
2. 单相型号是否应该把 R 相作为“平均电压/电流”需要产品定义；当前严格按三相平均规则，不对缺失相做推测。
3. 第二台 FH3X 的网络/Modbus 连接仍未恢复，尚未完成双设备真机实测。
4. 当前控制写入虽然有本地测试和模拟器验证，但商业发布前仍需在安全条件下做真机读回验证。
5. HACS 发布前必须决定独立协议库依赖如何公开安装，避免 Green 能运行但普通 HACS 用户无法安装。
6. 当前代码尚未提交本轮最终修改，也未创建 GitHub Release。
7. 当前未重新启用 FH3X 自定义前端面板。

## 七、给 DeepSeek 的继续工作提示

请基于本文档继续工作，并遵守以下边界：

1. 不要修改 PCS 地址 `2`、BMS 地址 `1`、实体唯一 ID 和旧配置项，除非同时提供迁移和回归测试。
2. 不要重新注册实验性 FH3X 前端面板。
3. 不要添加未经协议文档和真机验证的写入控制。
4. 任何协议地址必须区分绝对地址和 `0x1400` 区域相对偏移。
5. 通信超时、设备离线和协议不支持必须显示为 unavailable/stale，而不是零值或告警恢复。
6. 先运行本地测试，再部署 Green；部署前备份，失败时恢复备份。
7. 发布 HACS 前先展示最终 diff、测试证据、真机验证范围和已知限制，不要自动创建 GitHub Release 或 PR。
8. 若要改变单相平均值策略，先确认产品定义，再补充协议测试和实体说明。

## 八、相关资料

- [`FH3X项目交接文档.md`](FH3X项目交接文档.md)
- [`FH3X_HA使用文档.md`](FH3X_HA使用文档.md)
- [`FH3X产品点位映射矩阵.md`](FH3X产品点位映射矩阵.md)
- [`FH3X产品最新点位适配开发计划.md`](FH3X产品最新点位适配开发计划.md)
- [`HACS默认商店发布流程.md`](HACS默认商店发布流程.md)
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
- [`CORE_MIGRATION.md`](CORE_MIGRATION.md)

