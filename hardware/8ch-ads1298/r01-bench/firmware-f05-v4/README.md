# F05 的 C08D V4 构建变体 · 2026-10-30

**状态：已实现未验收。** 三档能编译、补丁自测通过；没刷机，P48X 板还在嘉立创审核（Y21）。硬件锁照旧关着（`MAKO_V12_AFE_ENABLED=0`，`bench_release.h` 的 `MAKO_BENCH_MEASURED 0` 不动），所以这版刷上去 ADS1298 **有电（V4 模拟电源常开）但保持 PWDN/RESET 低、不采样**，`start()` 直接回 `Locked`。

对象：P48X（V4 单颗 ADS1298，背面第二颗不贴）+ P44b 转接板（`../../c08-p44b-xiao-adapter-mini-20261027/pin-table.csv`）+ XIAO nRF52840 Sense。

## 为什么单独一个工程

同 `firmware-f05-c05p`：F05 的构建 ID 哈希 `firmware-f05/` 全部源文件，R01 不能动一个字节。`v4_build.py` 钉死 F05 `main.cpp` 的 sha256，按 8 处锚点替换（每处必须正好命中一次），生成到构建目录；`ads1298.cpp`、`v12_*.c` 用薄包装原样 `#include`。

## 和 R01 F05 的差异

| 脚 | R01 上 | P44b/V4 上 | V4 版做法 |
|---|---|---|---|
| D0 | 模拟电源使能 | CS_B（第二颗片选） | 开机起拉高，不再随启停拉低 |
| D1 | CLKSEL | 不接（V4 R17 下拉 → 外部 2.048 MHz X1） | `clocksel()` 空操作，D1 不驱动 |
| D3 | AVDD 分压采样（要 4.6–5.4 V） | START（10k 下拉） | 输出低；采集照旧用 START 命令 0x08 |
| D5 | 电源好（要读到低） | DRDY_B（背面不贴，悬空） | 下拉输入，不再参与电源判断 |

- `rails_good()` 恒为真：V4 的 ±2.5 V 由 XIAO 3V3 经 LM27762 常开，板上没有检测脚。电源是否正常只能靠台架实测，这正是硬件锁要等的证据。
- 采集中「D5 不为低就判电源故障停机」那一行去掉。
- 元数据加 `"board":"V4"`（同 C05P 加 `board` 的做法）；广播名不变。
- 寄存器不改：WCT1/WCT2（0x18/0x19）本来就写 0 并逐个回读（原厂固件残留的 WCT1=0x60 会被清掉，自测里断言）；CONFIG1 0x84/0x83 的 CLK_EN=0；CONFIG3 RLDREF 用外部——V4 U1 第 60 脚 RLDREF 接 AGND，即 ±2.5 V 的中点，读自 P48X `pcb-final.epru` 的 PAD_NET。

## 检查

| 检查 | 命令 | 结果（10-30 本机） |
|---|---|---|
| 补丁自测 | `python v4_build.py` | 8 处全命中、每条结果都在；D0 拉低、D1 驱动、`analogRead(D3)`、`digitalRead(D5)` 一处不剩；改过的 F05 main.cpp 被拒 |
| 编译 | `pio run -e v4_2k -e v4_4k -e v4_2k_imu` | 通过；Flash 127852 / 136056（IMU）字节，RAM 约 21 KB；镜像里有 `"board":"V4"` |
| R01 不变 | `git diff origin/main -- firmware-f05` | 空；CI `ci_firmware.sh` 照旧重编 R01 十档逐档比 hex |

## 没做的 / 上电前要做的

- 没刷机、没上板。上电顺序、DVDD/VCAP1/参考稳定时间要先按 `../BENCH-ACCEPTANCE.md` 的思路在 V4 上实测，再走独立复核解锁；本变体不解锁。
- XIAO 3V3 给 V4 供电的余量和噪声没核（P44 README 已列）。
- 主机端只认 8 路，本变体也是 8 路，不涉及第二颗。
