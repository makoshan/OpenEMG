# openEMG：iPhone + Apple Watch

状态：界面和处理链已实现，模拟器验证过；真机已装 测试真机 但未见画面；**手势模型未上手机**（2026-10-17）。

**目前能接到的数据只有合成流**（XIAO 测速固件 `v12/ble-probe/xiao-synth`、F04 合成固件），界面标「合成」：只有元数据 profile 为 `F05_ADS_CANDIDATE` / `C01_FIXED_CLOCK_LOCKED` 才算真实设备。 F05 真设备要先往控制特征写 `TST1/EXT1/EXR1` 才启动 ADS，而且硬件锁打开后才出数；本 App 不发控制命令，守住硬件锁。

## A 做什么

`手环 BLE（F01 包）` → `iPhone：v12_dsp 滤波 → 八路波形 + 每路 RMS → 放松判定` → `WatchConnectivity` → `Watch：当前手势 / AI 待确认卡`

| 屏 | 内容（设计稿 D1 + D3，Mako 2026-10-17 定） |
|---|---|
| iPhone 主屏 | 八路滚动波形（约 2 秒），右侧每路 RMS µV；顶部帧率与「手放松 / 在用力 · N 路」；底部当前手势卡 |
| 点开手势卡 | 六类概率条；模拟手势；模拟一条 AI 待确认、用食指/中指判定 |
| Watch | 平时大字显示当前手势与置信环；有待确认时切换为倒计时确认卡并震动；判定后显示 3 秒结果 |

## B 哪些是真的

| 项 | 来源 |
|---|---|
| 波形、RMS、放松判定 | 处理链与真设备相同：F05 同一份 `v12_dsp.c`（HP15/LP600/50 Hz 陷波，经桥接头直接编译），µV 按 ADS1298 参考 4.0 V、增益 6 换算；放松线 150 µV 与桌面版一致 |
| 六类手势与置信 | **模拟**，界面标出「模拟」；模型还没移植到手机 |
| AI 待确认 | **模拟**；真钩子在 `host/ai_confirm.py`，还没接到手机 |
| 数据来源标签 | XIAO 合成流读元数据 `synthetic` 标「合成」；模拟器无蓝牙时用演示数据标「演示」；收到第一帧前显示「等数据 / 未出数」 |
| 元数据异常 | 读不到、不是 JSON、fs 不是 2000/4000：报错断开并本次跳过这台，不猜采样率、不无限重连 |

## C 构建与检查

```bash
cd apple/openEMG && xcodegen generate
```

自检（Mac 上编 F01 拆包 + v12_dsp）：

```bash
cd apple/openEMG && mkdir -p build && swiftc -import-objc-header iOS/Bridging.h -Xcc -I../../hardware/8ch-ads1298/r01-bench/firmware-f05/src -Xcc -ffp-contract=off -o build/check check/main.swift iOS/Band.swift ../../hardware/8ch-ads1298/r01-bench/firmware-f05/src/v12_dsp.c && build/check
```

真机：Xcode 27.1 以上（手表 watchOS 27），构建时传 `DEVELOPMENT_TEAM`；iPhone 装好后，在手机「Watch」App 里给 openEMG 点安装。iOS 17 / watchOS 10 起。

## D 已验证 / 未验证

| 项 | 结果 |
|---|---|
| 自检 | 拆包 3 例；200 Hz 正弦滤波后 5619 µV（与理论一致），50 Hz 陷波后 9 µV；4 kHz 喂 3 秒：抽点数、RMS 5619 µV、reset 清零。改抽点间隔的变异会失败 |
| 独立只读复核 | 第一轮「修后可合并」：F05 需控制命令（文档已改）、出数前不显示已连接、标合成三项必须修已改；元数据严格、断开清零、新会话重置滤波、手表不对旧结果震动、确认时长共享常量也已改；第二轮「修后可合并」：profile 改白名单（F04 合成固件也标「合成」）、元数据失败跳过该设备、断开清 source、iOS「未出数」灰色，均已改 |
| Xcode 27.1 模拟器构建 | iOS、watchOS 两个目标通过 |
| iPhone 17 Pro 模拟器（iOS 26.3） | 主屏、点开概率视图、模拟待确认 → 拒绝 |
| 配对模拟器（iPhone Duo + Watch Ultra 3） | 手表收到待确认卡和常规手势视图（含帧率、放松状态同步）。iPhone Duo 上点不开面板，换普通 iPhone 正常，判为模拟器问题 |
| 未验证 | 真机 BLE 收流、手表上的同意/拒绝结果页、熄屏后的行为、手势模型 |
