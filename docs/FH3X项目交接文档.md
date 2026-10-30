# FH3X Home Assistant 项目交接文档

> 文档用途：供新负责人理解当前代码、测试方式、发布边界和已知风险。
> 本文档不包含密码、Token、私有 IP、设备序列号或受限制的协议原文。

## 1. 项目概况

FH3X 集成是 Pylontech Force H3X 户储系统的 Home Assistant 本地集成，通过 Modbus TCP 读取 PCS、BMS 数据并在 HA 中提供传感器、控制、告警和诊断实体。

当前范围：

- 本地 Modbus TCP，默认端口 `502`;
- PCS 设备地址 `2`，BMS 设备地址 `1`;
- 支持 HACS 自定义仓库安装，当前发布目标为 HACS 默认商店；Home Assistant Core 上游发布不在本阶段范围内。
- 不包含云账号、站点管理、蓝牙配网、OTA 和自定义前端面板。

## 2. 当前仓库和版本

| 项目 | 位置 / 值 | 说明 |
|---|---|---|
| HACS 集成仓库 | `/home/kubo/home_assistant` | 当前自定义集成主仓库 |
| 当前分支 | `fh3x/shared-library` | 不要默认当作 `main` 发布分支 |
| Integration domain | `pylontech_fh3x` | 配置项和实体前缀均依赖它 |
| 当前清单版本 | `0.6.26` | `custom_components/pylontech_fh3x/manifest.json` |
| 独立协议库 | `/home/kubo/pylontech_fh3x` | `pylontech-fh3x==0.1.0` |
| Core 迁移仓库 | `/home/kubo/home_assistant_core` | 历史实验目录，本阶段不作为发布目标 |

### 2.1 分支边界

- `/home/kubo/home_assistant` 是 HACS 自定义集成的当前开发仓库。
- `/home/kubo/pylontech_fh3x` 是独立 Modbus 协议库，不应在两个仓库重复实现协议解码。
- `/home/kubo/home_assistant_core` 仅保留历史实验代码；不要和 HACS 自定义集成同时加载，也不纳入本阶段验收。

### 2.2 当前主要风险

1. 当前 HACS `main` 只需安装 `pymodbus==3.13.1`；若未来合并 `shared-library` 分支，才需要额外提供 `pylontech-fh3x==0.1.0` 的公开安装来源。
2. 产品目前尚未完整确认最终实体矩阵；产品实体表中的 Key、默认展示、诊断分类和控制权限需要评审后才能定稿，不能直接重命名或批量开放。
3. 写入控制必须按实际协议、操作模式、读回校验和真机结果审核。
4. 不能把模拟器通过当作真机控制验证。

### 2.3 产品实体矩阵待确认项

产品评审至少需要为每个点位确认：

- 是否作为 HA 实体开放，以及实体类型：sensor、binary_sensor、number、select、switch 或 time。
- 显示名称、中英文翻译、单位、device_class、state_class、精度和正负号含义。
- 默认展示档位：日常、常用设置或高级/诊断；是否默认禁用。
- 只读还是可写；可写时的范围、步长、模式互锁、二次确认和读回规则。
- BMS/PCS 地址、寄存器、偏移、宽度、缩放、无效值和通信失败行为。
- 是否纳入 Energy Dashboard、长期统计、告警中心或仅用于诊断。
- 多机并联、未配置设备、协议不支持和不同固件版本下的可用性。

## 3. 代码架构

```text
Config Flow / Options
          |
          v
FH3XModbusClient  ---- Modbus TCP ---- PCS(ID 2) / BMS(ID 1)
          |
          v
FH3XCoordinator
          |
          +--> protocol decoder --> Sensor / Binary Sensor / Number / Select / Switch / Time
          |
          +--> AlarmEventTracker --> HA event bus / Logbook
          |
          +--> diagnostics --> 脱敏诊断下载
```

### 3.1 重要文件

| 文件 | 职责 |
|---|---|
| `__init__.py` | 创建客户端和协调器，转发平台，卸载时关闭连接 |
| `api.py` | 共享协议库的兼容导出层 |
| `protocol.py` | 寄存器地址、宽度、符号、比例和功率方向解析 |
| `coordinator.py` | 单轮轮询、异常恢复、写入串行化、读回刷新 |
| `sensor.py` | 能源、电池、电网、PV 和诊断传感器 |
| `binary_sensor.py` | 电网状态、PCS/BMS 告警和限制状态 |
| `number.py` | SOC、功率、前馈和削峰等数值控制 |
| `select.py` | EMS 模式和计划充放电模式 |
| `switch.py` | EPS、时段使能、热泵、削峰和工作日位控制 |
| `time.py` | 四个计划时段的开始/结束时间 |
| `profiles.py` / `exposure.py` | 实体和控制暴露档位及旧实体兼容 |
| `discovery.py` | FH3X 自定义 SSDP 组播/广播发现 |
| `config_flow.py` | 扫描、手动 IP、多设备、重配置和 Options |
| `alarm_history.py` | 告警触发、变化、恢复的状态跟踪 |
| `diagnostics.py` | 下载脱敏诊断数据 |
| `tests/` | 协议、轮询、控制、发现和告警回归测试 |

## 4. Modbus 与地址规则

- PCS 使用 Modbus device ID `2`。
- BMS 使用 Modbus device ID `1`。
- Modbus TCP 默认端口是 `502`。
- PCS 表中的地址按协议表使用绝对地址。
- BMS `0x1000` 和 `0x1100` 区域使用绝对地址。
- BMS 电池堆 `0x1400` 部分的表格值是相对偏移，必须加上 `0x1400` 基址。

已经特别校验的两个家庭负载累计电量地址：

| 类型 | 文档偏移 | 实际地址 |
|---|---:|---:|
| 单机系统 | `0x0691–0x0692` | `0x1A91–0x1A92` |
| 并机系统 | `0x06D1–0x06D2` | `0x1AD1–0x1AD2` |

具体覆盖请以 [`LOCAL_POINT_MATRIX.md`](LOCAL_POINT_MATRIX.md) 为准，不要从交接记忆或旧脚本直接修改地址。

## 5. 轮询、写入和数据可用性

- 默认轮询周期为 10 秒，Options 可配置为 5–300 秒。
- 所有实体共享一个协调器，避免每个实体独立读 Modbus。
- 写入使用锁串行化，写入后立即读回并刷新。
- 快速连续切换时，以设备读回的最终值为准，不使用乐观更新。
- 临时通信失败会保留最近有效数据，连续失败超过阈值后实体才会不可用。
- 通信超时不能被解释为告警恢复、零功率或累计电量归零。
- `TOTAL_INCREASING` 能源数据启动时需要二次确认，避免 Energy Dashboard 出现跳变。

## 6. 当前实体暴露档位

### 6.1 Entity detail

| 档位 | 适用人群 | 内容 |
|---|---|---|
| Recommended / Compact | 普通用户 | 核心 PV、负载、电网、电池功率、SOC、能源累计量、状态和告警 |
| Extended monitoring / Standard | 日常监控 | PV1–PV3、三相数据、温度、BMS 汇总和 EPS |
| Engineering diagnostics | 调试/工程 | 原始 bit、模块、电芯、串口及协议诊断 |

Compact 是默认档位，不意味着其他数据不支持，而是避免设备页默认被大量工程实体占满。

### 6.2 Control exposure

| 档位 | 控制内容 |
|---|---|
| Daily controls only | EMS、EPS 输出、计划 1–4 使能 |
| Daily controls and common settings | 上述控制 + 手动充放电功率、充电上限 SOC、并网/离网 EPS 保留 SOC |
| Advanced controls and full schedules | 完整时段、工作日、削峰、热泵和高级限制 |

### 6.3 Detailed BMS

默认关闭。开启后会读取 `0x1400` 电池堆、模块和电芯数据，请在汇总 BMS 读取稳定后再开启。

## 7. 发现与配置流程

FH3X 使用自定义 SSDP 格式，不注册 HA 标准 SSDP 集成。

- 组播：`239.101.1.250:1900`
- 组播源端口：`1901`
- 广播兼容路径：`255.255.255.255:10088`
- 最多发送 3 轮搜索，总窗口约 15 秒。
- 使用 USN 去重，无 USN 时使用 IP 去重。
- 发现后的确认页不再阻塞等待 Modbus 身份读取，设备加载后由正常轮询读取真实序列号。
- 发现失败、已配置、或网络隔离时，始终保留手动 IP 配置入口。

## 8. 告警和诊断

当前主要告警实体：

- Inverter fault
- Inverter warning
- BMS protection
- BMS alarm

告警属性包含可读名称、稳定 issue ID、原始 bitmask、未知 bit、错误码和首次/最后观测时间。触发、变化、恢复会写入 HA Logbook，通信失败不会被误认为恢复。

诊断下载前必须检查并确保已脱敏：主机地址、序列号、网络拓扑、凭据和备份文件不应公开发布。

## 9. 交接开发工作流程

1. 先在协议库中完成寄存器解析和单元测试。
2. 再在集成中添加或调整实体描述、翻译和暴露档位。
3. 写入控制必须同时覆盖编码、串行化、读回、失败和最终状态。
4. 先用 Modbus Slave 测试正常、超时、异常值和快速切换，再用真机做安全的读取和少量控制验证。
5. 变更实体唯一 ID、寄存器地址、控制方向或累计量逻辑时，必须补充迁移和回归测试。

## 10. 本地检查

```bash
cd /home/kubo/home_assistant
python3 -m compileall -q custom_components tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
ruff check custom_components tests scripts
ruff format --check custom_components tests scripts
```

Core 分支另外运行 Core 项目规定的 Hassfest、pytest、翻译生成和 pre-commit，不能用自定义仓库单元测试代替。

## 11. 交接时必须传递的材料

- 当前代码分支、最后提交和未提交文件清单；
- 协议库版本、仓库地址和依赖版本；
- Green 或模拟器的测试方案和结果；
- 真机型号、PCS/BMS 固件版本、拓扑和控制验证范围；
- 当前已知限制、暂未验证的寄存器和禁止操作清单；
- 不包括任何密码、API Token、完整序列号、私有抓包和主机备份。
