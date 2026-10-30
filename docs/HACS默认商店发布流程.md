# FH3X HACS 默认商店发布流程

本文档只描述将 FH3X 集成提交到 HACS 默认商店的流程。
发布前必须完成代码测试、Green 验证和人工确认。
本项目当前不以 Home Assistant Core 上游集成为发布目标；`ha core rebuild` 仅用于 Green 依赖安装验证。

## 0. 当前进度（2026-09-14）

### 已完成

- HACS 集成目录、manifest.json、hacs.json、README、LICENSE 和 CHANGELOG 已建立。
- 当前集成版本为 0.6.26，Domain 为 pylontech_fh3x。
- 已配置 HACS Action、Hassfest、Python 测试、Ruff 和仓库元数据检查工作流。
- 已完成配置流、自动发现、手动 IP、传感器、控制、告警、诊断和多语言基础功能。
- 已建立独立 pylontech-fh3x 协议库，当前协议库主分支可访问且工作区干净。
- 已完成项目交接文档和 Home Assistant 使用文档。
- 已在 Green 完成 GitHub `main` 的集成目录重装、HA 重启、Core 重建和 0.6.17→0.6.26 文件级回滚验证。
- 已创建 Green 回滚保护备份 `2e24b2f7`，并确认 FH3X Modbus TCP 目标端口可达。
- 已完成协议点位和现有实体的初版映射，但产品尚未确认最终实体范围、默认展示和控制权限。

### 进行中

- 有正式 Tag/Release 后的 HACS 页面升级、卸载和回滚验证。
- 当前 HACS `main` 使用 `pymodbus==3.13.1`；共享协议包仅属于未纳入本阶段发布的 `shared-library` 分支。
- 当前 0.6.26 版本的最终测试记录、兼容性记录和真机信息整理。
- 清理并提交本次文档和产品资料的归属变更。

### 本次已执行的验证

- 集成编译检查：通过。
- 集成单元测试：68 项通过。
- 独立协议库测试：38 项通过。
- 仓库元数据校验：通过。
- 协议包 wheel 构建：通过，生成 0.1.0 包。
- Ruff：未通过，api.py 存在 15 个导入排序/未使用导入问题。
- 公共包索引：尚未找到 pylontech-fh3x，干净环境依赖安装仍未通过。
- Green 网络：ICMP 和 SSH 2222 端口可达；本轮已使用当前凭据登录并开始验证。

### 2026-09-14 Green 验证结果

- Green SSH：设备为 Home Assistant Green，HA OS 18.2，Supervisor 2026.09.0，Core 2026.7.4。
- 备份：已创建全量备份 `FH3X pre-validation 20260914`，slug 为 `2e24b2f7`，用于本次回滚保护。
- 全新文件安装：已将现有集成目录移入验证备份，并从 GitHub `main` 下载 zip 后重新安装；归档下载成功，manifest 为 0.6.26，文件数量 27。
- 依赖加载：重启 HA 后没有出现 `pymodbus` 缺失、导入失败或 FH3X 集成设置失败日志；manifest 要求 `pymodbus==3.13.1`。
- Core 重建：执行 `ha core rebuild` 后 Core 仍为 running，manifest 依赖解析未报错。
- 升级/回滚：临时切换 Green 上的 0.6.17 备份并重启，再恢复 0.6.26 并重启；两次 Core 均回到运行状态，配置项和实体注册文件保留。
- 真机连接：配置目标为 `172.22.194.39:502`；从 Green SSH 网络确认 TCP/502 可达，HA 日志未出现新的导入或依赖错误。当前未执行写入控制，读数仍需在实际 Modbus 设备稳定响应时持续观察。
- HACS 网络：Green 可下载 GitHub `main` zip；此前日志中的提交号 404、Raw GitHub 超时属于 HACS 网络/版本元数据问题，需在正式版本标签和稳定网络后复测。

### 尚未开始

- 当前仓库还没有正式的版本 Tag 和 GitHub Release。
- 尚未向 hacs/default 提交默认 Integration 列表 PR。
- 尚未进入 HACS 默认商店审核和索引刷新阶段。

### 当前阻塞项

1. 必须修复 api.py 的 Ruff 错误，并重新执行全部检查。
2. Green 本轮已完成文件级全新安装、0.6.17→0.6.26 回滚验证，但仍需有正式版本标签的 HACS 升级验证、长时间读数稳定性和真实控制读回验证。
3. 产品尚未完整定义需要开放的实体、传感器、控制项、默认启用状态和诊断范围，必须先完成实体矩阵评审。
4. 发布前工作区必须只保留经过确认的代码和文档；当前仍有交接文档及产品提供的 PDF/XLSX 未提交文件。
5. 必须先确认产品 PDF/XLSX 是否允许公开分发，未获授权的协议资料不能进入公开仓库。

说明：`pylontech-fh3x==0.1.0` 目前不是 HACS `main` 的阻塞项；只有将 `shared-library` 分支合并到发布分支时，才需要先提供该包的公开安装来源。

### 提交默认商店前的最短路径

    0.6.26 最终测试
        -> Green 全新 HACS 安装
        -> 修复测试发现的问题
        -> 更新版本和 CHANGELOG
        -> 创建 v0.6.26（或下一个正式版本）Tag/Release
        -> 等待 HACS Action/Hassfest 全部通过
        -> Fork hacs/default 并提交 Integration 列表 PR
        -> 完成审核和索引验证

## 1. HACS 默认商店的工作方式

HACS 默认商店只保存仓库索引，不复制 FH3X 代码。

用户流程：

    HACS 默认列表
          |
          v
    搜索 Pylontech Force H3X
          |
          v
    HACS 找到 pylontech-sw/HA-pylontech-force-H3X
          |
          v
    从 FH3X GitHub Release 下载
          |
          v
    安装到 custom_components/pylontech_fh3x

因此必须同时保证：

- HACS 默认索引能够找到仓库；
- 原 GitHub 仓库可访问；
- GitHub Release 格式正确；
- Release 中包含完整的 custom_components/pylontech_fh3x；
- 用户可以在干净 HA 环境中完成安装和配置。

## 2. 仓库基本要求

提交前确认以下内容：

- GitHub 仓库为公开仓库；
- 默认分支稳定且可以安装；
- 集成目录为 custom_components/pylontech_fh3x；
- Integration domain 为 pylontech_fh3x；
- manifest.json 中的名称、版本、文档和依赖正确；
- hacs.json 存在且类型为 Integration；
- README 包含安装、配置、实体、控制、升级和故障排查说明；
- LICENSE 存在；
- CHANGELOG 记录当前版本变化；
- 有明确的维护者和 issue 入口；
- 没有密码、Token、数据库、备份、私有 IP、抓包或未授权协议文件。

## 3. HACS 收录前代码检查

在 HACS 仓库执行：

    cd /home/kubo/home_assistant
    python3 -m compileall -q custom_components tests scripts
    python3 -m unittest discover -s tests -v
    python3 scripts/validate_repository.py
    ruff check custom_components tests scripts
    ruff format --check custom_components tests scripts

必须确认：

- 所有测试通过；
- 没有通过忽略失败或删除测试来“修复”结果；
- strings.json、英文和简体中文翻译同步；
- 实体 Unique ID 没有无迁移重命名；
- PCS 地址 2、BMS 地址 1 和 Modbus 地址没有意外变化；
- 写入控制具备范围、单位、模式限制、读回和失败测试；
- 通信超时不会被误判为告警恢复、零功率或累计量归零；
- 不支持的寄存器不会伪造为 0 或 off。

检查仓库状态：

    git status --short --branch
    git diff --check
    git diff --stat

## 4. 依赖检查

当前集成依赖独立协议包 pylontech-fh3x。

发布前必须在全新 Python/HA 环境确认：

- pylontech-fh3x 对应版本可以安装；
- pymodbus 依赖可以解析；
- Home Assistant 启动时不会出现 ModuleNotFoundError；
- HACS 下载后不需要开发机本地路径才能运行；
- 集成卸载后不会残留无法导入的模块。

如果依赖没有公开可安装来源，不得提交默认商店申请。
应先发布协议包，或将运行时必需代码放回集成目录。

## 5. 版本发布准备

### 5.1 修改版本号

发布新版本时同步修改：

- custom_components/pylontech_fh3x/manifest.json；
- CHANGELOG.md；
- Git Tag；
- GitHub Release。

例如发布 0.6.27，四处必须全部使用 0.6.27。

### 5.2 更新 README

README 至少要说明：

- 支持的 FH3X 型号和通信方式；
- Modbus TCP 默认端口；
- PCS/BMS 设备地址；
- HACS 安装步骤；
- 手动 IP 添加方法；
- 自动发现限制；
- 实体详细级别；
- EMS、EPS、SOC 和计划控制；
- Energy Dashboard 配置；
- 告警和 Logbook；
- 已知限制；
- 升级和回滚方法；
- 安全注意事项。

### 5.3 更新 CHANGELOG

CHANGELOG 应写用户能理解的变化：

- 新增功能；
- 修复问题；
- 实体或控制变化；
- 兼容性变化；
- 已知限制；
- 测试环境。

不要在 CHANGELOG 中写入私有 IP、完整序列号、密码或内部抓包。

## 6. 自动检查

仓库的 GitHub Actions 至少应包含：

- HACS Action；
- Home Assistant Hassfest；
- Python 编译和单元测试；
- Ruff 检查和格式检查；
- 仓库元数据检查。

提交 PR 或推送版本后，必须等待所有检查完成。

出现失败时：

1. 打开失败的 Action 日志；
2. 判断是仓库结构、manifest、翻译、代码还是测试问题；
3. 在本地复现；
4. 提交修复；
5. 重新等待全部检查完成。

不能使用跳过检查、忽略失败或只检查单个 Job 的方式提交。

## 7. Green 发布前验证

默认商店申请前，至少用 Green 完成一次完整验证。

### 7.1 安装验证

- 从 HACS 自定义仓库安装当前候选版本；
- 重启 Home Assistant；
- 确认集成可以加载；
- 确认配置流可以打开；
- 确认自动发现和手动 IP 均可用；
- 确认设备可以创建；
- 确认实体可以正常更新。

### 7.2 能源验证

- 光伏供家庭负载；
- 光伏给电池充电；
- 电池给家庭负载放电；
- 电网购电；
- 家庭向电网馈电；
- PV、Grid、Battery 和 Load 功率方向正确；
- kWh 累计实体没有启动跳变；
- Energy Dashboard 使用的是 kWh 实体，而不是 W 实体。

### 7.3 控制验证

至少验证：

- EMS 模式读取；
- EPS 开关读取和安全读回；
- SOC 限值读取和安全读回；
- 计划 1 的启用、时间、充放电模式和功率；
- 快速连续修改后的最终状态；
- 写入失败时界面显示设备真实状态；
- 不支持的控制显示不可用，而不是显示虚假关闭。

高风险控制（重启、AFCI 清除、继电器、工厂参数、紧急停机）没有明确真机批准时，不得在发布测试中操作。

### 7.4 告警验证

- PCS fault；
- PCS warning；
- BMS protection；
- BMS alarm；
- 多 bit 同时触发；
- 未知 bit；
- 告警恢复；
- 通信中断不误记为恢复；
- HA Logbook 和实体属性一致。

### 7.5 记录测试环境

测试记录应包含：

    FH3X 型号/拓扑：
    PCS 固件：
    BMS 固件：
    Home Assistant 版本：
    HACS 版本：
    集成版本：
    测试开始和结束时间：
    测试结论：
    已知限制：

公开提交中不得出现完整序列号、私有 IP 或访问凭据。

## 8. 创建 GitHub Release

1. 将测试通过的代码合并到稳定分支。
2. 确认工作区干净。
3. 创建与 manifest 一致的 Tag，例如 v0.6.27。
4. 推送 Tag。
5. 创建 GitHub Release，并选择对应 Tag。
6. Release 必须是正式 Release，不要只创建 Tag。
7. Release 说明包含：
   - 版本号；
   - 主要变化；
   - 升级注意事项；
   - 兼容性；
   - 测试结果；
   - 已知限制。
8. 不要上传协议原文、数据库、完整诊断、私有抓包或 HA 备份。

HACS 默认商店会从这个 GitHub 仓库读取 Release，Release 内容必须可以被用户直接使用。

## 9. 提交 HACS 默认商店

### 9.1 Fork 默认索引仓库

1. Fork hacs/default 到个人 GitHub 账号。
2. 在默认 Integration 列表中添加：
   pylontech-sw/HA-pylontech-force-H3X
3. 保持列表格式和排序规则与上游一致。
4. 提交可由维护者编辑的 Pull Request。

### 9.2 PR 内容

PR 中说明：

- 集成名称；
- GitHub 仓库；
- 支持的设备；
- 本地 Modbus TCP 特性；
- 已通过的 HACS Action 和 Hassfest；
- GitHub Release 地址；
- Green 测试结果；
- 已知限制。

不要把内部协议文档、测试账号、完整设备信息或私人网络信息放进 PR。

### 9.3 审核期间

- 持续关注自动检查；
- 及时回答维护者问题；
- 根据意见追加 commit；
- 不要强制修改已经公开的 PR 历史；
- 不要在审核期间引入与收录无关的大功能；
- 如果修改了仓库结构、manifest 或版本，应重新跑完整测试。

### 9.4 合并后

- 等待 HACS 默认索引刷新；
- 用普通用户视角搜索集成；
- 不输入 Custom repository，直接搜索名称；
- 从默认商店完成安装；
- 重启 HA 并重新验证设备配置；
- 检查升级提示是否能够识别新 Release。

## 10. 版本升级流程

默认商店收录后，每次升级仍按以下流程：

1. 建立功能分支；
2. 编写测试；
3. 修改代码和翻译；
4. 跑本地检查；
5. 在 Green 或模拟环境验证；
6. 更新 manifest、CHANGELOG、README；
7. 合并稳定分支；
8. 创建正式 Tag 和 GitHub Release；
9. 等待 GitHub Actions；
10. 再通过 HACS 升级验证。

不要只推送 commit 而不创建 GitHub Release，否则 HACS 可能无法正确识别版本升级。

## 11. 回滚流程

1. 先保存当前 HA 备份和诊断信息；
2. 在 HACS 中选择 FH3X 集成；
3. 选择 Redownload 或旧版本；
4. 选择上一个正式 Release；
5. 重启 Home Assistant；
6. 检查实体唯一 ID、能源统计和控制状态；
7. 如果同时修改过外部协议包，必须回滚到匹配的协议包版本。

不要通过删除设备、删除实体或重建配置来代替版本回滚，这可能造成历史统计和自动化引用断裂。

## 12. 发布阻断条件

出现以下任一情况，暂停 HACS 默认商店申请或版本发布：

- 全新 HACS 安装失败；
- 依赖包无法在干净环境安装；
- HACS Action、Hassfest 或单元测试失败；
- manifest、Tag、Release 版本不一致；
- 能量累计量有未解释跳变；
- 控制没有读回验证；
- 不支持的实体被伪造成 0 或 off；
- 告警通信中断被误记为恢复；
- Green 长时间运行仍频繁不可用；
- 发布内容包含敏感数据或未确认可分发的协议资料；
- 真机验证尚未完成，却在 Release 中声称已完成。

## 13. 最终检查清单

- [ ] 仓库公开且默认分支稳定。
- [ ] HACS Action 通过。
- [ ] Hassfest 通过。
- [ ] 单元测试、编译、Ruff 通过。
- [ ] manifest.json、CHANGELOG、Tag、Release 版本一致。
- [ ] README 安装和使用说明完整。
- [ ] 独立协议包可在干净环境安装。
- [ ] Green 全新安装通过。
- [ ] Green 重启、升级、卸载和回滚通过。
- [ ] 自动发现和手动 IP 添加通过。
- [ ] 核心能源流和 Energy Dashboard 无回归。
- [ ] EMS、EPS、SOC、计划控制读回正确。
- [ ] 告警、恢复和 Logbook 正常。
- [ ] 没有敏感信息或受限协议资料进入公开仓库。
- [ ] HACS 默认仓库 PR 已由负责人最终确认。
