# FH3X 产品点位映射矩阵

更新时间：2026-09-18  
来源：`HA可参考注册实体.xlsx` 及当前已验证的 PCS/BMS 解码结果。

本矩阵用于产品点位与 HA 实体的对照。已有实体的唯一 ID、单位和符号约定优先保持兼容；产品表中无法确认寄存器含义、单位或机型适用范围的点位暂不注册为可用实体。

## 已接入

| 产品点位 | HA 实体 key | 数据来源/处理 |
| --- | --- | --- |
| 设备型号 | `device_model` | PCS 身份块，使用已验证的身份读取结果 |
| 设备序列号 | `device_serial_number` | PCS 身份块，作为设备稳定身份 |
| 额定输出功率 | `rated_power` | PCS 扩展信息 `pcs_max_output_power` |
| 最大允许充电功率 | `max_charge_power` | BMS 最大允许充电电压 × 最大允许充电电流 ÷ 1000，单位 kW |
| 最大允许放电功率 | `max_discharge_power` | BMS 最小允许放电电压 × 最大放电电流 ÷ 1000，单位 kW |
| 设备故障状态 | `device_fault_status` | 故障优先于告警，状态为 `normal`/`alarm`/`fault` |
| 设备故障/设备告警 | `binary_sensor.device_fault` / `binary_sensor.device_alarm` | 基于同一聚合状态，故障时不同时显示告警 |
| PCS 运行状态 | `pcs_state` | 复用已解码的 PCS 状态 |
| 交流总视在功率 | `ac_total_apparent_power` | 复用 PCS AC 视在功率 |
| 交流功率因数 | `ac_power_factor` | 复用 PCS 功率因数 |
| 电网无功功率 | `grid_reactive_power` | 复用电表无功功率并按产品表换算为 kvar |
| 第三方电表有功功率/累计电量 | `third_party_meter_power` / `third_party_meter_energy` | 复用 PCS 监控块 |
| 逆变器交流有功/无功功率 | `inverter_power` / `inverter_reactive_power` | 复用 PCS AC 功率，按产品表换算为 kW/kvar |
| 交流频率 | `ac_frequency` | 复用 PCS 频率；不强行解释为电网或逆变器内部频率 |
| AC R/S/T 电压电流 | `ac_phase_*` | 复用已验证的三相 PCS 监控值 |
| 电表 A/B/C 相电压 | `meter_phase_*_voltage` | 复用 PCS 扩展电表电压 |
| 电表电网频率 | `meter_grid_frequency` | 复用 PCS 扩展电表频率 |
| BMS SOC/SOH/温度 | `battery_soc_bms` / `battery_soh` / `battery_temperature` | 复用 BMS 汇总寄存器 |
| 光伏功率/累计发电量 | `pv_power` / `pv_generation_energy` | 复用现有 PV 总功率并按产品表换算为 kW，累计能量保留 kWh |
| 逆变器累计发电量 | `inverter_generation_energy` | 复用 PCS AC 输出累计电量 |
| 逆变器累计耗电量 | `inverter_consumption_energy` | 根据负的 AC 有功功率按采样间隔积分；通信间断不积分 |
| 第三方光伏功率 | `third_party_pv_power` | `acc_power_r + acc_power_s + acc_power_t`，换算为 kW |
| 当前告警代码 | `current_alarm_code` | 合并 PCS 故障/告警码与 BMS 错误码，保留具体码值 |
| 日/月统计 | `daily_*` / `monthly_*` | 由累计量基线差计算，基线和累计值通过 HA Storage 持久化 |

## 兼容映射

产品表中的以下名称已经由现有实体覆盖，不创建重复实体：

- `pv_power` 与现有 `pv_total_power`；
- `pv_generation_energy` 与现有 `pv_total_energy`；
- `operation_mode` 与现有 `ems_mode`；
- `schedule_*` 与现有 `period_*`；
- `battery_capacity` 与现有并机 PCS / 单机 BMS 容量选择逻辑；
- `grid_power`、`battery_power`、`grid_import_energy`、`grid_export_energy` 等核心能源实体。

原有实体 ID 不迁移，避免破坏自动化、Energy Dashboard 和历史统计。

## 暂时隔离

以下点位不能仅凭当前表格安全注册：

- `max_reactive_power`：充电/放电寄存器已知，但协议未明确单位；
- `site_import_limit`、`site_export_limit`：表格标为只读，BMS 地址/适用范围需产品确认；
- `third_party_pv_generation_energy`：`0x06ED–0x06EE` 的基地址/偏移及单机适用性需确认；
- 设备故障/告警中的未知 bit：实时告警仍保留 `Unknown alarm bit N`，不映射为未经确认的中文含义；
- 单相机型的 B/C 相点位：没有型号能力证据时保持不可用，不显示 0；
- 任何新的写入寄存器：必须先补充范围、符号、互锁、读回和真机验证记录。

## 展示档位

- **Compact**：保留核心功率、电量、SOC/SOH、容量、并网状态、频率和设备故障状态。
- **Standard**：增加允许充放电功率、BMS 温度、PV/AC/电表三相数据以及日/月统计。
- **Engineering**：增加身份、额定功率、PCS 状态、视在功率、功率因数、第三方电表、告警码和工程诊断。

不支持或读取失败的可选块保持不可用；不会用零值填充。
