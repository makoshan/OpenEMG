# R01 一镜像两通道固件（离体台架）

软件候选，未刷机、未实测。2026-10-24 Mako：不再为换模式频繁刷机，蓝牙版和 USB 版合成一个镜像，复核后只刷一次。

## A · 怎么选通道

```
[开机] → 读 VBUS
  ├─ 插着 USB → USB 串口（F05-USB 原程序，主机用 firmware-f05-usb/usb_capture.py）
  └─ 只接电池 → 蓝牙 DOUT（firmware-f05-ble-dout 原程序，2048 帧队列，经 C6 接收器）
↓ 运行中插/拔 USB → 整片复位，重启后按新供电重选；不续采
```

## B · 每种供电能做什么

| 命令 | 插 USB | 只接电池 |
|---|---|---|
| META / DIAG / STOP | ✓ | ✓ |
| PWR1 / TST1 / SHT1 | ✓（J1-12 须临时跨接到 J1-14，否则报 Rails） | ✓ |
| EXT1 / EXR1（J3 外部输入） | ✗ 构建时去掉了 F05-USB 的 EXR1，镜像里查不到才放行 | ✓ |
| LOF1（外部输入 + RLD + 直流导联检测） | ✗ | 只有 `build.py --loff` 出的镜像认；默认镜像拒绝 |
| 人体 | ✗ | 仍须满足 SINGLE-FAULT-R01.md §4 并由 Mako 确认 |

J1-12 互锁仍是硬件，固件绕不过；插 USB 做采样仍要动那根线，测完恢复。

## C · 实现

- build.py 先调两版各自的 stage()（各自钉哈希、打补丁不变），再把两份 main.cpp 改名成 ble_app.cpp / usb_app.cpp（setup/loop → ble_/usb_ 前缀），入口 src/dispatch.cpp 分流。
- 共享 ADS 驱动、锁头等 6 个文件两版必须逐字节相同，否则停构建。
- EXR1（外部输入 + 右腿驱动）只让 CH1 进 RLD 平均（RLD_SENSP/N=0x01，F05 原为 0xFF）：R01 人体只接 CH1，其余 7 路悬空会把 RLD 拉偏。要换通道改 build.py 的 RLD_SENS。
- SPI 两半都写死 2 MHz（USB 程序原默认 1 MHz，DOUT 读帧需 2 MHz）。
- 两份程序都有 struct BoardHal，同名类会被链接器静默合并（初版 USB 模式因此跑了蓝牙版 HAL，复核抓到）：构建时改名 BleBoardHal/UsbBoardHal，并用 nm 检查两个目标文件没有任何同名外部符号，有就停。
- 蓝牙模式下 SoftDevice 管着 POWER 外设，VBUS 经 sd_power_usbregstatus_get 读；读失败按插着 USB 处理（复位）。
- USB 模式下 `usb_setup()` 后检查 `USBREGSTATUS.OUTPUTRDY==1 && NRF_USBD->USBPULLUP==0`，若成立则补调 `tusb_hal_nrf_power_event(2)`（`USB_EVT_READY`，同 `bluefruit.cpp:88`）：引导程序（如 1200bps 串口 DFU `0x4e` 3s 超时退回）已清过 `EVENTS_USBPWRRDY` 后软跳回应用时，板包 `Adafruit_TinyUSB_nrf.cpp:132` 只发 `DETECTED(0)` 不发 `READY(2)` 会令 `USBPULLUP` 停在 `0` 致设备从 Mac 消失。
- 运行中插 USB 是直接复位，不像单独蓝牙版那样先停机、发尾包和停机状态；主机看到的是断连（Incomplete）。复位后 GPIO 回到断开输入，D0（ANA_EN）由 R25 下拉，模拟电源关、ADS 掉电。

## D · 自检与构建

```
python check.py
python build.py --pio <pio> --toolchain platformio/toolchain-gccarmnoneeabi@1.120301.0 [--loff]
```

check.py：入口分流 8 例（电池开机→蓝牙、USB 开机→USB、引导程序退回补拉 USBPULLUP、已拉起不重发、插/拔都复位、蓝牙下经 SoftDevice 读 VBUS、读失败按插着）+ 蓝牙流控 17 组 + USB 帧自检 + 下面 E 节的 S3/S4 测试。镜像只留本地 artifacts/。

## E · 寄存器快照与 LOF1（TI 计划 S3+S4，2026-11-09，软件候选，未构建镜像、未刷机）

计划见 `docs/ti-evm-to-openemg-plan-20261109.md`。补丁在 `bench_patch.py`，build.py 的 stage() 最后打在暂存副本上；`firmware-f05`、`-ble-dout`、`-usb` 原文件和它们各自的检查都不动。

| 改动 | 蓝牙半边 | USB 半边 |
|---|---|---|
| S3 寄存器快照：写完寄存器、开连续读之前读回 0x00–0x19（连续读期间芯片不理读寄存器命令），到下一次 start 才清 | 状态特征 v3：163 字节 = v2 的 136 + 有效标志 1 + 寄存器 26；主机 `host/v12_status.py` 解出 `ads_regs`。元数据加 `"lof1"`、`"regs_snapshot":"status_v3"`（替身里 428 字节，上限 511） | 停机报告最后多一帧 META `{"diag":8,"valid":…,"regs":"52 位十六进制"}`（放最后，不挤掉 diag:3/4）；采集中用 `Waavv` 改过的寄存器以 diag:5 为准 |
| S4 LOF1 = EXR1 + LOFF=0x03（95%、电流源、6 nA、直流）+ LOFF_SENSP/N = RLD_SENS + CONFIG4=0x02，LOFF_FLIP=0 | 只在 `--loff` 镜像（编译开关 `MAKO_R01_LOFF=1`）里认；命令解析、流控模式白名单、驱动输入白名单三处都按开关拦 | 没有；构建时查 USB 源码里不许出现 EXT1、EXR1、LOF1 任何一个；运行时启动前再拦一道，只许模式 1、2（内部信号） |

- 状态 v3 牵连的主机检查已一起改：`v12_status`（认 163/3）、`v12_ble`（停机快照版本 ≥ 2）、`v12_dongle`（长读重读认 163），各有正反样本。旧 48/64/136 照读。
- 归档只认**停机快照**：蓝牙重连后第一份状态里还是上一次会话的快照（标志仍为 1），到下一次 start 才清。
- 给 S5 记一笔（推断，未实测）：LOF1 打开导联比较器后，CONFIG3 的只读位 RLD_STAT 可能读成 1，共享驱动的 `write_checked(3,0xE4)` 是整字节比对，会报 Readback 停机。属于安全方向的失败，和 `host/v12_ble.py` 里记的 EXR1 风险同类；真遇到再在驱动里给 0x03 屏蔽 bit0。
- 构建后护栏只查源码字符串和 `platformio.ini`：镜像里查 `LOF1` 字串不可靠（4 字节 `memcmp` 可能被编译成整数比较），等真编镜像时再看。
- LOF1 只离体：`SINGLE-FAULT-R01.md` 第 14 行的前提是导联脱落电流源为 0；要上人体先重算。`--loff` 镜像清单里 `lof1: true`、文件名带 `-lof1`；人体会话前刷回默认镜像并用 `--expected-build-id` 核对。
- 测试（check.py）：
  - 驱动替身逐字节对快照，默认镜像拒绝 LOF1、`--loff` 镜像的导联寄存器对，打印的整表交给 `host/ads1298_regs.py` 按手册查，0 问题；
  - 蓝牙半边整份编译，状态 v3、LOF1 命令和流控白名单按开关；
  - USB 半边 `send_regs()` 单独编译（-Werror），经 F05-USB 的 Python 解析器解出 diag:8；
  - USB 外部输入检查三种模式各一条反例；
  - 替身开机处于连续读、收到 0x11 才响应读写，快照缓冲先填满 0xEE，确认 26 个都被覆盖。
- 变异测试 `check_bench_mutations.py`：24 个（补丁 20 + 主机 4）全部被抓到。在临时副本里改，不碰工作区，约 40 s，不挂 check_all。
- 镜像（2026-11-09 构建，源码 = 主干 1946aa4d5；PlatformIO 6.2.0 用 `uv tool install platformio` 重装在 `~/.local/bin/pio`；工具链用 platformio.ini 默认，和板上 `4a1cc01e` 同一套）。镜像只留本地 `artifacts/`：

  | 镜像 | build_id | hex sha256 | DFU sha256 | 用途 |
  |---|---|---|---|---|
  | 默认 | `092258e327847e97` | `63fb1f2f3cf17d2d…` | `7d14e65c7e2b6260…` | 可替换板上 `4a1cc01e`：只多了寄存器快照，不认 LOF1 |
  | `--loff` | `b27ed1ed8d69cad0` | `d7499d575a592104…` | `1edf1ab2c0ba73c3…` | 只离体台架；人体会话前刷回默认镜像并核 build_id |

- 构建核对：
  - 可复现：同一套环境把改动前的主干 308f421b3 重编，build_id `4a1cc01ebe9ae091`、hex sha256 `f7598f3f…` 和板上那版逐字节一致；默认镜像重编两次，sha256 也一样。
  - 补丁进了镜像：两个新镜像里都有 `"lof1":%s`、`"regs_snapshot":"status_v3"`、`{"diag":8,...}` 格式串，`4a1cc01e` 里没有。
  - 开关生效：命令字被编译成整数比较，镜像里查不到 `LOF1`/`EXR1` 字串；改看反汇编，`--loff` 镜像的 `control_write` 多 14 条指令、带常量 7，`Ads1298::start` 多 15 条、带 7 和 0x03，默认镜像里都没有。
  - 另用 README D 节写的 12.3.1 工具链（`--toolchain …@1.120301.0`）也编通过（build_id `88c344464f8bc388`），没放进 artifacts：板上那版用的是默认工具链。
- 2026-11-09 21:16 Mako 同意后把默认镜像 `092258e327847e97` 刷进 R01（`host/r01_flash.py`，11 s）：刷前经 USB 读 META 是 `4a1cc01ebe9ae091`，刷后读回 `092258e327847e97`，fault None。刷前差点插成蓝牙接收器（产品名 `MAKO-DONGLE`，VID/PID 相同），刷机脚本已加拒刷。
- 没做：状态 v3 和 `diag:8` 还没实采验证（USB 采样要临时跨接 J1-12，蓝牙要拔 USB、插接收器）；`--loff` 镜像没刷。
