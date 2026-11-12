# 单通道固件：Cheez sEMG-D + ESP32-S3

App「单通道 · Cheez + ESP32-S3」用的采集固件。没有自制 PCB：成品 Cheez 模块用 4 根杜邦线接开发板。2026-10-16 从 tiny-ai-watch原样迁来，旧仓只留历史。

## 接线

| 模块脚 | 开发板 | 作用 |
|---|---|---|
| V | 5V 排针 | 模块要 5V |
| G | GND | 共地 |
| S（白） | 1 kΩ 后接 GPIO4 | 模拟肌电，ADC1 |
| L（黄） | GPIO5 | 佩戴检测，高电平 = 戴着 |

电极是一体三条：EMG+ / REF / EMG−，REF 在中间，贴前臂屈肌腹，三条顺着肌纤维方向。

- USB 插标 COM 的口（CH340，VID 0x1A86，Mac 上是 `/dev/cu.usbserial-*`）。原生 USB 口不给排针 5V。
- 5V 排针默认只进不出，要先桥正面的 IN-OUT 焊盘。没桥时模块 V–G 只有 0.43 V，采到的 50 Hz 波形是引脚悬空感应。
- ESP32 ADC 最高约 3.16 V，模块用力时在 3.1–3.3 V 之间的削顶看不到。

## 构建与刷机

```bash
pio run -d firmware/cheez-s3 -e emg_usb_s3 -t upload
```

串口命令（115200）：`?` 横幅、`p` 每秒探测、`s` 实时流、`r` / `R` / `V` 录 2 s。主机端是 `host/usb_emg.py`、`host/emg_web.py`。

## 实测记录（2026-09-27，旧仓 HANDOFF）

离体静息 1634 mV、摆幅 12 mV；贴肤摆幅 80–90 mV；L 高 = 戴着。迁仓后只做了编译，没有重新上板。
