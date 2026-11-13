# 蓝牙接收器：XIAO nRF52840 当主机收 CH585M 2 kHz（2026-10-21）

P0：Mac 自带蓝牙作主机时连接间隔固定 30 ms，CH585 2k 丢 28–32%。换成自己控制连接参数的接收器（Meta 论文原文 "communicates to a computer using a Bluetooth receiver"），CH585M 评估板在 2 kHz × 8 路 × 24 位下能不能零丢包。

## A 数字（CH585M-EVT 刷 tput_big，XIAO 接收器经 USB 送 Mac）

| 跑法（全部 2M PHY、MTU 247、DLE 251） | 丢失率 | 净吞吐 | 最长停顿 | 每秒样本（最少–最多） | 实际连接间隔 | 对账 |
|---|---:|---:|---:|---:|---|---|
| **2k、7.5 ms、600 s** | **0**（1,200,944 收 / 0 缺） | 384.0 kbps | 28.7 ms | 1976–2016 | 7.5 ms（CH585 自报 + 接收器读回） | 闭合；IMU 62,449/62,449 |
| 2k、7.5 ms、60 s | 0 | 384.1 kbps | 30.0 ms | 1976–2016 | 7.5 ms | 闭合；原始字节回放结果一致 |
| 2k、7.5 ms、60 s（v2 接收器，评估板改充电宝供电） | 0 | 384.1 kbps | 29.4 ms | 1976–2024 | 7.5 ms | 闭合；窗口内接收器 0 丢帧、0 次重连 |
| 2k、15 ms、600 s | 0 | 384.0 kbps | 58.6 ms | 1960–2040 | 15 ms | 闭合；外设背压 145 次、队列峰值 16/128 |
| 4k、7.5 ms、120 s | **24.7%** | 577.0 kbps | 27.3 ms | 2832–3080 | 7.5 ms | 闭合（设备队列丢 118,864 = 电脑缺口）；外设背压 16,092 次、队列峰值 128/128，接收器 0 丢帧 |
| 4k、7.5 ms、120 s（v2） | 28.5% | 547.8 kbps | 28.1 ms | 2592–3016 | 7.5 ms | 闭合；背压 16,097、队列峰值 128，接收器 0 丢帧 |
| 4k、15 ms、120 s（v2） | 27.7% | 554.4 kbps | 59.2 ms | 2536–3088 | 15 ms | 闭合；背压 7,907、队列峰值 128，接收器 0 丢帧 |
| 对照：Mac 直连 2k（D0，10-21） | 28–32% | 258.7–273.8 kbps | 89–269 ms | | 固定 30 ms（Mac 不接受改短） | 闭合 |
| 对照：Mac 直连 XIAO 2k（D0） | 12.6% | 336.8 kbps | 84 ms | | 未读到 | 无状态特征 |

结论：**接收器定 7.5 ms 或 15 ms 时，CH585M 2 kHz × 8 路 × 24 位 10 分钟零丢包（已实测通过）**；Mac 直连丢 28–32% 的原因是 Mac 固定 30 ms 间隔，不是 CH585。**4k 在 7.5 ms 下送不满**（达成 75%），卡在 CH585 发送侧：每个 7.5 ms 连接事件平均只发出约 2.8 包（4k 需要 3.75 包），外设 BLE 缓冲常满、接收器从未丢帧；**换 15 ms 也没用**：7.5 ms 和 15 ms 下 CH585 都只送出约 360–375 包/s（约 690 kbps 应用层）。

4k 瓶颈排查（10-21 晚，已实测部分 + 推断）：
- CH585 自报连接事件 133.9 次/s（7.5 ms）、65.7 次/s（15 ms），一次不缺；每事件平均 3.44 包 / 7.07 包（含 IMU 小包），按 2M 空中时间折算只用了每个间隔的 **约 55%**（4.1/7.5 ms、8.4/15 ms）。
- DLE 不是原因：接收器读回 SoftDevice 的 DLE 生效值，收发都是 251 B / 2120 µs。
- 1M 对照（30 s）：只到 117 包/s、每事件约 0.9 包，即一个 2.5 ms 的包都塞不满半个间隔，同样符合「只用约一半间隔」。
- 接收器这边 SoftDevice 事件长度配 30 ms、开着事件扩展（Bluefruit 源码核过），理论上允许用满整个间隔。
- **中心侧排除（已实测，4k 30 s）**：接收器事件长度 30 ms+扩展 → 352–363 包/s（3.36 包/事件@7.5 ms，7.04@15 ms）；7.5 ms → 370 包/s（3.49）；关扩展 → 367 包/s（3.47）；阳性对照 2.5 ms+关扩展 → 14 包/s，读写也超时。即中心的事件长度设置确实管用，但放宽它不涨，**限速在 CH585 一侧**。实验档在 `xiao-central/platformio.ini`（`dongle_evt6`、`dongle_noext`、`dongle_evt2_noext`），默认 `dongle` 档不变。
- 推断（CH585 侧具体原因未证实）：协议栈作从机时每个连接事件只发约半个间隔，可能是给连接事件回调（我们在这里补包）留时间。tput 固件已加两个运行时开关待测：`FIL1`（每 625 µs 在 TMOS 主循环里补包，不只在事件结束时补）、`CEL`+n（连接事件长度参数，文档写给中心用，试一下从机是否也看），用 `tput.py run --cmd FIL1 --cmd CEL:24` 发；另编了 `tput_huge`（缓冲 48、每事件 40 包）。**这三项都还没刷进评估板**：10-21 晚两次按 DOWNLOAD 插 Mac，Mac 都没识别到 USB 设备（板子有电、跑的是旧固件），疑似线只供电或没在上电瞬间按住。
- 对 2k 的含义：2k 每事件要 2.65 包，容量约 3.44 包，**余量只有约 1.3×**；桌面实测零丢包，但有干扰重传时余量可能不够，戴身上前要复测。两次 4k 7.5 ms 差 3.8 个百分点（24.7% / 28.5%），第二次评估板改用充电宝供电，原因未查。

判据：`missing_samples=0`、`closure.closed=true`（设备发出 = 电脑收到，设备队列丢弃 = 电脑缺口 + 尾部缺口，IMU 发出 = 收到）。停顿用接收器收到通知的时刻量（nRF TIMER2 1 µs 计时），不受 USB 批量送达影响。每秒曲线在各 run 的 `per_second.jsonl`。

**USB CDC 带宽余量（已实测）**：`tput.py usbbench` 让接收器连续灌 248 B 帧 5 s，Mac 收到 **496.9 kB/s**，0 字节丢失。需求按帧头 8 B 算：2k = 250 包/s × 240 B + IMU 104 × 44 B ≈ **64.6 kB/s（余量 7.7×）**；4k ≈ **124.6 kB/s（余量 4.0×）**。瓶颈在 Adafruit TinyUSB 的 256 B 发送 FIFO（USB 全速理论约 1 MB/s），2k/4k 都够，不改。

## A2 接 R01（2026-10-23，`dongle_r01` 档 + `host/v12_dongle.py`）

R01 离体板（`firmware-f05-ble-dout`，电池供电，内部测试源 TST1，2k）。Mac 直连 30 ms 时丢 3.5–13%；换这块接收器定 7.5 ms：

| 跑法 | 有效样本 | 缺失 | 接收器丢帧 / 缓冲峰值 |
|---|---:|---:|---|
| 60 s | 120,087 | 0 | 0 / 1518 B |
| 20 s × 2 连续 | 28,117 / 28,122 | 0 / 0 | 0 |
| 600 s | 1,199,902 | 0 | 0 / 1761 B |

- `dongle_r01` 档：目标名 `MAKO-V12-ADS-2K`；IMU 特征改为可选（F05 不开 IMU）；应答缓冲 260→600（F05 元数据超过 260 字节，原来会截断）。
- `dongle_1292_2k` / `dongle_1292_4k` 档：目标名 `MAKO-V12-1292-2K` / `MAKO-V12-1292-4K`（接 `xiao-ads1292-2ch` 两路板 + P44e + XIAO，同样开 `DONGLE_PEER_MTU` 由外设发起 MTU 247）。
- `dongle_c08b` 档：目标名 `YUANLI-C08B`（接 `firmware/c08b-stream` 共用双核主控 2/8/16 路流式候选固件；C08B nRF 从机等待中心发起 `MTU=247` 请求，因此本档不加 `DONGLE_PEER_MTU`，并同时转发 `DATA` 与 `IMU_DATA` 通知到 `host/c08b_stream.py --port auto`）。
- 新增 `D` 命令：每次采集前断开重连。F05 只在新连接上从头开始数据流，同一连接上第二次采集会发“重新配置”边界，新开的主机会话会拒收（实测）。
- `host/v12_dongle.py`：把接收器串口包装成 `v12_ble.capture` 用到的几个 Bleak 接口，校验、解码、缺失统计全部复用 `v12_ble`。开采后接收器重连计数一变就按断连处理，不拼接两条连接的数据。`python host/v12_dongle.py selftest` 自检切帧。
- 用法：`python host/v12_dongle.py --port /dev/cu.usbmodemXXX --mode test --seconds 60 --expected <R01 build_id> --out <新目录>`。

## A3 XIAO ESP32-C6 版接收器（2026-10-24，`c6-central/`）

ESP-IDF v6.1 + NimBLE，串口协议与 `xiao-central` 逐字节相同，`host/v12_dongle.py` 不改。R01 = `firmware-f05-ble-dout` 构建 `5c6aaa04e3963c9e`（Codex 流控版），电池供电，USB 拔掉。

| 跑法 | 有效样本 | 缺失 | 结果 |
|---|---:|---:|---|
| TST1 60 s | 120,108 | 0 | 通过 |
| TST1 600 s | 1,199,741 | 0 | 通过：计数闭合，接收器丢帧 0，串口杂字节 0 |
| SHT1 600 s | 567,224（第 284 s 停） | 0 | **失败：R01 故障码 7（Overrun）**，见下 |
| TST1 60 s（复核修复后） | 120,097 | 0 | 通过：计数闭合 |

两个坑（都已修，都是实测出来的）：
- **C6 不能主动协商 MTU**：R01 开始采集时自己会发起一次；两边都发起时，R01 的 SoftDevice 发通知一直返回 8（INVALID_STATE），一个包也发不出去。另外，NimBLE 要开外设角色和 GATT 服务端（`CONFIG_BT_NIMBLE_ROLE_PERIPHERAL`、`GATT_SERVER`），否则 R01 发来的 MTU 请求没人回。链路帧里的 MTU 要等 R01 开始采集后才从 23 变成 247。
- **链路帧必须经环形缓冲**：原来链路帧直接写串口。若环形缓冲里的数据帧只写出一半，链路帧就插进它中间，导致第 22 s 有 2 帧状态字无效（坏包里能看到 `a5 11 1a00`）。

SHT1 失败分析：停机前约 6 s，接收器每秒只收到 222–238 包（需要 250 包），R01 的 F01 队列攒满 512 帧，中断队列也满到 16 帧，按设计报 Overrun 停机，没有静默丢样本。同一 600 s 内，每秒收包最多只有 274 包，即每个 7.5 ms 连接事件约 2.05 包，余量只有约 10%。R01 一侧已配 `configPrphConn(247,100,16,…)`，事件长度不是瓶颈。限速在哪一侧（C6 控制器，还是 R01 的 SoftDevice）**未查明**。10-23 用 nRF 接收器跑 SHT1 时缺的 226 帧，可能也是这个原因（推断）。

独立复核（子代理，只读）：没有 P0。已修：`reply` 的静态缓冲被两个任务共用，长读没有“进行中”标志，`I` 命令不校验范围，长读上限比电脑端切帧上限多 1 字节。没修：`scan()` 失败后不重试；链路帧每秒才发一次，断连最晚 1 s 后才发现（`connects` 计数兜底，数据不会拼接）。

```bash
cd firmware/ble-dongle/c6-central
source ~/esp/esp-idf-v6.1/export.sh
idf.py -p /dev/cu.usbmodem101 flash          # C6 在 Mac 上显示为 USB JTAG_serial debug unit
python host/v12_dongle.py --port /dev/cu.usbmodem101 --mode test --seconds 60 --expected 5c6aaa04e3963c9e --out <新目录>
```

## A4 换回 nRF52840 Sense 接收器（2026-10-28）

R01 自己也是 XIAO nRF52840 Sense，USB VID/PID 和接收器相同（0x2886/0x8045），主机分不出。`platformio.ini` 加 `board_build.usb_product = MAKO-DONGLE`，`host/r01_exr1_eval.py` 按 C6 的 VID 或这个产品名认接收器，R01 插着 USB 照样拦。

- 已实测：备用板刷入 `dongle_r01` 后 Mac 枚举为 `MAKO-DONGLE`，`--port auto` 自动识别，`Q` 应答正常（未连 R01）。
- 坑（10-29 实测）：接收器连上后主动协商 MTU，R01 开采时也发起一次，R01 第一个通知就返回 8（INVALID_STATE），报故障 9 取消。和 A3 的 C6 是同一个坑；`dongle_r01` 加 `DONGLE_PEER_MTU`，不再主动协商，由 R01 发起。
- 已实测：修后连 R01（`4a1cc01ebe9ae091`，只接电池）跑 TST1 60 s，R01 产生 = 发出 = 收到 108,114 样本，缺 0，故障 0，计数闭合；链路 7.5 ms / 2M / MTU 247 / DLE 251，接收器丢帧 0、缓冲峰值 1440 B。60 s 窗口只有约 54 s 数据，原因未查（C6 10-24 同口径为 120,108）。归档 `host/v12-captures/r01-nrfdongle-tst1-60s-20261029-001647`（本地）。
- 刷接收器：在 `xiao-central/` 里 `pio run -e dongle_r01 -t upload --upload-port <接收器端口>`，端口要写明，R01 同时插着时别让它自动挑；接收器停在引导程序（PID 0x0045）时直接 `adafruit-nrfutil dfu serial -pkg <zip> -p <端口> -b 115200 --singlebank`。
- `host/r01_flash.py` 只刷 R01（11-09 起）：认出产品名 `MAKO-DONGLE` 就拒刷；没给 `--serial` 时引导程序态和应用态的 XIAO 同时在也拒刷。拦不住两种：10-28 前刷的、没设产品名的老接收器，和只插着一块停在引导程序的接收器。

## B 四态

| 项 | 状态 | 证据 |
|---|---|---|
| 接收器固件编译 | 已实测通过 | `xiao-central/` `pio run`：RAM 20%、Flash 15% |
| 接收器连 CH585、定参数 | 已实测通过 | 链路信息读回 7.5 ms / 2M / MTU 247 / DLE 251；CH585 状态特征自报间隔 7.5 ms、PHY 2/2 |
| `tput.py --serial` + 自测 | 已实测通过 | selftest 新增：录好字节流回放零丢失、任意切块结果一致、**故意丢一帧报 8 个样本缺口且对账不闭合**、垃圾字节计数、接收器时间戳量 900 ms 停顿、计时器回绕、字节级假接收器端到端（含间隔不到位必须拒测）；6 个变异（时间戳改用电脑时刻、特征号错配、不计垃圾字节、不核间隔、不处理回绕、半帧丢弃）全部使自测失败 |
| 在线结果与回放一致 | 已实测通过 | 2k 60 s 录下的原始字节 `replay` 出同样的样本数、缺口、最长停顿 |
| 2k 7.5 ms 60 s / 600 s、15 ms 600 s 零丢包 | 已实测通过 | A 表，`../ch585m-ble-20261018/runs/dongle-*`（600 s 两条用的是 v1 接收器，v2 只多了断连检测、HFXO 和链路帧的 connects 字段，数据通路没改；v2 复测 60 s 同样零丢包） |
| 4k 零丢包 | 阻塞（CH585 发送侧） | 7.5 / 15 ms 都只到约 72–75%，接收器 0 丢帧；要改 tput 固件 |
| 独立只读复核 | 已实测通过 | 子代理复核：无 P0；P1（测量中断开又自动重连会被拼接）已修，加了自测和变异；P2 已修：收尾断线照写 summary、串口读失败标断开、打开先清残留、报告只算测量窗口、用连接前核 connected()、TIMER2 请求 HFXO。没修：请求/应答不带序号（目前没有超时后重发的路径，不会触发） |
| 用到真 C05 胶囊板、人体 | 未实现 | 只用开发板合成数据；硬件锁照旧 |
| 接收器进 OpenEMG App 采集链 | 未实现 | 本次只做测速；App 侧要接串口帧格式另开 PR |

## C 怎么跑

前置：CH585M-EVT 刷 `tput_big`（见 `../ch585m-ble-20261018/README.md` D 节），XIAO 刷本接收器。只用开发板，不接 AFE，不戴身上。走串口不需要终端蓝牙权限。同一时间只一个采集者（`tput.py run` 查 OpenEMG 采集服务等进程，串口用独占方式打开）。

```bash
cd firmware/ble-dongle/xiao-central
pio run -t upload --upload-port /dev/cu.usbmodem1101
```

Adafruit 内核支持 1200 波特触发复位，已在跑本固件或 synth 固件时可直接上传；XIAO 卡死时再双击 RST 进 UF2。

```bash
cd v12/ch585m-ble-20261018
PY=.venv/bin/python
$PY -I -B host/tput.py usbbench --serial /dev/cu.usbmodem1101
$PY -I -B host/tput.py run --serial /dev/cu.usbmodem1101 --rate 2000 --seconds 600 --out runs/dongle-2k-2m-7p5ms-600s
$PY -I -B host/tput.py run --serial /dev/cu.usbmodem1101 --rate 2000 --ci 12 --seconds 600 --out runs/dongle-2k-2m-15ms-600s
$PY -I -B host/tput.py replay 录下的.bin     # run 加 --record 文件 时录原始字节
```

`--ci` 在串口模式下是接收器直接定的间隔（1.25 ms 单位，默认 6 = 7.5 ms），不发给外设；脚本等接收器报告实际间隔到位才开始，不到位就拒测。

## D 协议

设备→电脑：`A5 | kind u8 | len u16 LE | t_us u32 LE | payload`。kind 2 = 数据特征通知原样、6 = IMU 特征通知原样、0x10 文本日志、0x11 链路信息（每秒一帧：已就绪、实际间隔、PHY、MTU、DLE、目标间隔、环形缓冲丢帧数、通知数、缓冲峰值）、0x80|op 命令应答（首字节 0 成功）、0x7F 带宽测试填充。

电脑→设备：`A5 | op u8 | len u16 LE | payload`。`W` 写控制特征（T2K0/T4K0/STOP/PHY1/PHY2/CI 原样转发，带应答写）、`R` 读特征（3 元数据 / 4 状态）、`I` 设连接间隔、`Q` 立即回链路信息、`B` USB 带宽测试。

接收器行为：只按扫描应答里的名字 `MAKO-CH585-TPUT` 连（真 F05 用同一服务 UUID，靠名字挡掉；`tput.py` 还会核元数据 profile）。连上先发现服务并订阅数据和 IMU，再由主循环逐项补请求 2M PHY → DLE → MTU 247 → 连接间隔（同时发会撞 BUSY，这是首版连不上的原因）。CH585 固件连上 1 s 后会自己请求 15–30 ms，Bluefruit 默认照收，主循环发现间隔不是目标值就每 0.5 s 改回来。通知在 BLE 任务里只拷进 32 KB 环形缓冲，主循环写 USB；缓冲满丢整帧并计数，电脑同时能从序号缺口和对账看到。

## E 风险与限制

1. 合成数据、开发板、桌面上近距离；没测距离、人体遮挡、2.4 GHz 干扰（Wi-Fi 同屋照常开着）。
2. 接收器是 nRF52840 + SoftDevice S140 7.3.0；量产接收器换别的芯片要重测。
3. 请求/应答不带序号：一次命令超时后，迟到的应答可能被下一个同类命令接走。现在超时就直接报错退出，不会触发；以后要做重试就得先加序号。
4. 帧没有校验和：USB CDC 链路层自带 CRC，实测垃圾字节 0；对不齐吞掉的包会变成序号缺口，只多报不漏报。
5. 停顿量的是接收器收到通知的时刻，不含 USB 到 Mac 的延迟（实时显示的端到端延迟另测）。

## F 文件

| 路径 | 内容 |
|---|---|
| `xiao-central/platformio.ini` | 板型、板包与 xiao-synth 一致，复用 F05 的 verify_board.py（Bluefruit 断连补丁、构建 ID） |
| `xiao-central/src/main.cpp` | 接收器固件 |
| `../ch585m-ble-20261018/host/tput.py` | `run --serial`、`replay`、`usbbench`；`SerialClient` 对 `run()` 呈现 BleakClient 接口，统计和对账代码不变 |
| `../ch585m-ble-20261018/runs/dongle-*` | 实测结果（合成数据，可入库） |
