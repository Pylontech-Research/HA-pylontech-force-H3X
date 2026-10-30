# FH3X Home Assistant 使用文档

## 1. 使用前准备

1. Home Assistant 主机可访问 FH3X 的局域网地址。
2. FH3X 已开启 Modbus TCP。
3. TCP 端口默认为 `502`，不要将它暴露到互联网。
4. 建议在路由器中为 FH3X 设置 DHCP 保留，避免设备 IP 变化。
5. 只允许一个集成实例连接同一个 Modbus 网关，避免多个 HA 实例同时轮询。

## 2. 安装集成

### 2.1 HACS 自定义仓库

1. 打开 HACS。
2. 选择“自定义仓库”。
3. 输入集成仓库地址：`https://github.com/pylontech-sw/HA-pylontech-force-H3X`。
4. 类型选择 `Integration`。
5. 下载 **Pylontech Force H3X**。
6. 重启 Home Assistant。
7. 进入 **设置 → 设备与服务 → 添加集成**。

### 2.2 手动安装

1. 将仓库中的 `custom_components/pylontech_fh3x` 复制到 HA 配置目录的 `custom_components/` 下。
2. 重启 Home Assistant。
3. 在集成页面选择 **Pylontech Force H3X**。

HACS 和手动安装不要同时保留两份集成文件。

## 3. 添加设备

### 3.1 自动发现

点击添加后，集成会通过 FH3X 自定义 SSDP 寻找设备。多台设备时会展示设备名、 USN 和 IP 供选择。

如果搜索不到，常见原因是 Wi-Fi 隔离、VLAN 组播过滤、不同网卡路由或防火墙禁止 UDP。此时选择手动输入地址，不要通过全网段扫描 502 端口。

### 3.2 手动配置

- IP 地址：FH3X 当前局域网 IP。
- 端口：默认 `502`。
- 手动配置会读取 PCS 身份信息，并以设备序列号作为唯一标识。

### 3.3 重新配置

设备 IP 变化时，打开设备的集成配置，选择重新配置，修改 IP 和端口。集成会校验新地址仍是同一台 FH3X，不应用新设备地址替换其他设备。

## 4. 首次配置建议

### 4.1 轮询周期

- 默认：10 秒。
- 调试或实时监控：可调低到 5 秒，但请先确认设备和网关能承受请求频率。
- 不稳定或网关性能较弱：可提高到 15–60 秒。

### 4.2 实体详细级别

- **Recommended**：适合日常使用，只显示核心数据。
- **Extended monitoring**：需要监控 PV 分路、三相、温度和 EPS 时使用。
- **Engineering diagnostics**：只建议调试和故障排查时开启，避免主页出现大量原始数据。

### 4.3 控制暴露级别

- **Daily controls only**：保留 EMS、EPS 和四个时段开关。
- **Daily controls and common settings**：默认推荐，增加手动功率和 SOC 限值。
- **Advanced controls and full schedules**：增加完整计划、工作日、削峰和热泵控制。

### 4.4 详细 BMS

只有在 BMS 汇总数据稳定后才开启 **Detailed module and cell data**。开启后会增加很多禁用的诊断实体，这是预期行为。

## 5. 设备页和能源数据

### 5.1 主要实体

- PV 总功率：当前光伏输出，单位 W。
- Home load power：家庭当前负载，单位 W。
- Grid power：电网功率，正值为购电，负值为馈电。
- Battery power：电池功率，正值为放电，负值为充电。
- Battery SOC：电池荷电状态。
- Grid connected：依据 PCS AC 输出子状态识别并网或备电。
- Battery capacity：并机使用 PCS 总容量，非并机回退 BMS 标称容量。

### 5.2 Energy Dashboard 配置

进入 **设置 → 仪表板 → 能源**，建议如下配置：

| Energy Dashboard 项目 | FH3X 实体 |
|---|---|
| 太阳能源 | PV total energy |
| 电网取电 | Grid import energy |
| 返回电网 | Grid export energy |
| 电池充电 | Battery charge energy |
| 电池放电 | Battery discharge energy |

这些实体是 kWh 累计量，不要把 W 单位的实时功率添加到 Energy Dashboard。`Home load energy` 为设备或集成提供的家庭负载累计量，不建议与 HA 根据其他流程自动推导的家庭用电重复配置。

如果历史统计出现大跳变：

1. 确认选择的是 kWh 实体，不是 W 实体。
2. 检查实体的 `state_class` 是 `total_increasing`。
3. 检查设备重启后累计值是否继续保持。
4. 不要频繁删除重新创建实体，否则会创建新的统计周期。

## 6. 控制功能使用

### 6.1 EMS 模式

- **Self-consumption**：优先光伏供负载，多余电量给电池充电。
- **Backup**：优先保留电池电量用于备电。
- **Off-grid**：按离网或备电逻辑运行，实际行为以设备固件为准。
- **Feed-in priority**：优先向电网馈电。
- **User**：允许使用手动充放电功率参考值。
- **PN customer**：供特定客户策略使用，不要在不清楚固件行为时随意切换。

### 6.2 手动功率

`Charge/discharge power reference` 的单位是额定功率百分比，不是 W。当前范围为 `-100%` 到 `100%`，且只在 EMS 为 `User` 时允许修改。请避免反复点击实时电池控制，先通过读回值确认方向和效果。

### 6.3 EPS 和 SOC

- 并网 EPS 保留 SOC：并网时为备电保留的最低 SOC。
- 离网 EPS 保留 SOC：离网运行时保留的最低 SOC。
- EPS 输出开关在普通并网模式下可能不生效，这不一定是 HA 写入失败。

### 6.4 四个计划时段

每个时段包含：使能、开始时间、结束时间、充电/放电、目标功率和星期位。

- 功率是 `%Pn`，不是瓦。
- 时段不应重叠。
- 快速修改多个星期时，每次修改后应等待读回结果。
- 如果控件立即弹回，先查看 HA 错误消息和设备实际读回值，不要按界面显示猜测设备状态。

## 7. 告警、历史和诊断

### 7.1 查看当前告警

打开 **设置 → 设备与服务 → Pylontech Force H3X → 实体**，查看：

- Inverter fault
- Inverter warning
- BMS protection
- BMS alarm

点击实体后，在属性中可看到具体告警名称、原始 bitmask、错误码和未知 bit。

### 7.2 查看历史告警

1. 在 HA 左侧进入 **Logbook / 日志簿**。
2. 按实体筛选 FH3X 告警实体。
3. 告警触发、位变化和恢复会以事件方式保存。

历史保留时间由 HA Recorder 的 `purge_keep_days` 决定，集成不单独创建数据库。

### 7.3 诊断下载

设置 → 设备与服务 → FH3X 设备 菜单 → 下载诊断。上传前请脱敏 IP 和序列号，不要附带 HA 整体备份。

## 8. 常见问题

### 设备不可用

1. 从 HA 所在主机测试 FH3X IP 和 TCP `502`。
2. 确认 Modbus TCP 已开启。
3. 确认没有其他 Modbus 客户独占网关。
4. 先重新加载集成，再根据日志判断是路由、端口还是协议问题。

### 自动发现不到

检查 Wi-Fi 隔离、VLAN 和多网卡路由。可直接选择手动 IP，不要扫描整个网段。

### 实体显示灰色

灰色通常表示该固件或拓扑不提供对应寄存器。请区分：

- 通信失败：大多数实体同时不可用；
- 功能不支持：只有特定扩展实体不可用；
- 详细数据未启用：开启 Detailed BMS 或详细实体档位。

### 能量图跳变

优先检查单位是否为 kWh、是否选错了实时 W 实体，以及重启后累计量是否丢失。如果只有一次跳变，请先下载诊断检查原始计数器。

### 控制修改后弹回

控制会写入、读回、刷新。弹回代表设备最终状态没有保存，常见原因是：

- 当前 EMS 模式不允许该控制；
- 设备固件不支持该寄存器；
- 参数超出设备范围；
- 连续快速写入触发设备互斥。

## 9. 升级、回滚和卸载

- 升级前先创建 HA 备份并记录当前集成版本。
- HACS 升级后重启 HA，检查配置项、设备可用性、累计量和控制权限。
- 不要通过删除重新添加设备来解决普通故障，这可能会导致新的唯一 ID 和新的历史统计。
- 自定义集成和 Core 集成不应在同一个 HA 配置中同时安装，因为两者使用同一个 domain。

## 10. 安全注意

- Modbus TCP 本身不提供传输加密和身份认证，只在可信局域网使用。
- 不要把 TCP `502` 映射到公网。
- 不要把密码、Token、序列号、公网 IP 和原始抓包发到 GitHub 问题或论坛。
- 写入 EMS、SOC、EPS 和计划时段前，确认当前是模拟器还是真机。
- 真机上的重启、AFCI 清除、继电器和工厂参数不在普通用户操作范围内。

