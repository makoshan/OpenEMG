# V12 F05：ADS1298离体采样候选

状态：已实现未验收。未刷机；默认硬件锁定，不用于人体。

| 项目 | 已实现 | 仍需实物 |
|---|---|---|
| ADS | 2k/4k、27字节原帧、ID/配置读回、测试源/短接/外部输入 | 时序、8通道顺序、实际电源/参考稳定 |
| BLE | 原帧排队、连接代次检查、同步控制回调、启动取消 | 持续吞吐、背压、重连、关断延迟 |
| 时间 | TIMER2 1µs分辨率，首帧ISR服务时间、后续标称周期；异常间隔停采 | 中断延迟、GPIO边沿合并造成的漏计 |
| IMU | 独立／联合双流候选，原包与回放；见[IMU说明](IMU.md) | Sense实物版本、真实新鲜度与同步误差 |

控制特征写入 `TST1`、`SHT1`、`EXT1`、`EXR1` 、`IMU1` 或 `STOP`。默认前四项均被硬件锁拒绝；IMU1仅在另两档IMU候选可用。
`EXR1`（2026-10-05 加）= 外部输入 + 右腿驱动：RLD_SENSP/N=0xFF（8 对全进平均），其余配置读回、参考等待之后最后一步写 CONFIG3=0xE4 开 RLD；RLDREF 仍用板上外部分压。`EXT1` 不开 RLD，两者同板对比 50 Hz 残留。RLD 环路稳定性未实测。
`src/bench_release.h` 的参考等待0表示没有实测值，不是无需等待。不要直接解除锁。
供电/VCAP1/参考稳定证据闭合后填写实测保守等待值，再重新编译、核ID、离体验收。

复现：`c++ -std=c++17 -Wall -Wextra -Werror src/ads1298.cpp test_ads1298.cpp -o /tmp/v12-r01-ads-test`；运行测试应报告30项通过（含 RLD 最后开启、读回失败断电两项反例；ID 只比低 6 位 `(ID&0x3F)==0x12`，ADS1298 0x92、ADS1298R 0xD2、类比 AFE948 0x12 放行，0x91/0xB2/0x00/0xFF 拒绝；另以 6 个变异驱动核对测试会失败）。
`pio run -e ads_2k -e ads_4k` 后运行 `python3 collect.py`，会检查源码哈希、镜像ID、HEX与DFU一致性，并拒绝过期输入。
构建清单见 `build-manifest.json`；大镜像仅留本地 `artifacts/`，不随源码入库。

独立代码复核关闭了首帧等待、跨连接旧命令、启动取消三项阻塞；没有进行设备验收。取消允许当前短SPI操作完成，不承诺零延迟关断。

## 2026-10-05 C 配置边界修复

F05真实ADS帧不置SYNTHETIC。首次会话flags=2；同BLE连接切换配置后首包flags=6（bit1 SESSION_START + bit2 RECONFIGURE），seq=0，保留原单调时钟。只有前一会话首包已成功发送才携带边界；STOP后再启动、通知重试均保留边界。旧排队数据在重配时清除，边界丢样数未知，不计作精确0。首次订阅或重连仍用普通SESSION_START。旧版主机不识别bit2，会拒绝，须同步升级本仓host和codec。

Receiver记录边界两侧时间，拒绝未标记的重启、重复/倒退时间边界、合成与实采混用；V12Rig仅清空文本块，离线DSP新段重置并预热。在线stream8/预测器尚未接入边界事件，本轮不保证在线窗口隔离。原始包中的边界标记随RawArchive落盘。

GPIO回读只比GPIOC低4位；其他配置仍保持原检查。实际输入电平高4位不再触发假Readback，低位错误仍停机。芯佰微ID兼容未核，本轮未放宽0x92身份检查。（2026-10-22 已改为 `(ID&0x3F)==0x12`，兼容类比 AFE948，见上方复现说明。）

主机验证：编译test_stream_boundary.c、src/v12_stream.c、src/v12_codec.c、src/v12_dsp.c（cc -std=c11 -Wall -Wextra -Werror，链接-lm）；输出hex存临时文件，再用项目Python运行host/check_v12_configuration.py该文件。另运行ADS25例、offline-f01/check.py、dsp-f03/check.py、host/v12.py --check及emg_gate单测。

B的SPI速率矩阵、DRDY最短间隔上报见下节；不动R01硬件，不刷机，默认硬件锁不变。

## 2026-10-05 B 台架诊断准备

`MAKO_V12_SPI_HZ`默认2MHz，候选仅1/2/4/8MHz；元数据新增`spi_Hz`。默认`ads_2k`、`ads_4k`即2MHz；另有`ads_2k_spi1/spi4/spi8`及`ads_4k_spi1/spi4/spi8`六环境。这只是实验速度，不代表实物能可靠运行。

状态特征由48扩为64字节，小端；前48字节字段位置保留，byte43从0变为版本1。新客户端须支持64字节读取；旧版严格按48字节读取的客户端须升级。

| 偏移 | 宽度 | 字段 |
|---|---:|---|
| 0/8/16/24/32 | 各8 | produced/ring_dropped/scheduler_skipped/sent_samples/notify_failures |
| 40/41/42/43 | 各1 | fault/active/bench_measured/状态格式版本 |
| 44 | 4 | 最近ADS状态字 |
| 48 | 8 | 本次capture开启后的DRDY原始下降沿数 |
| 56 | 4 | 最短沿间隔µs；不足两沿时0xFFFFFFFF表示未测，不填0 |
| 60 | 4 | SPI Hz |

统计包含最终被拒绝的假沿；故障/STOP保留，真正重新开启capture才清零。ISR时间是软件服务时间，不能当作物理边沿；中断被合并、线束干扰或逻辑分析仪时序仍须实物核对。最短间隔0表示同一µs内两次ISR，和未测不同。64位计数由短关中断区取快照，区间里不编码或传输BLE。

电脑端独立解析器`host/v12_status.py HEX`支持旧48/新64字节，未知版本/长度/非法SPI/自相矛盾沿数拒绝；标记`physical_device_verified=false`。它不会连接设备，已接入host/v12_ble.py状态轮询；在线页面尚未接入。`host/check_v12_status.py`实际编译固件编码函数，输出交给Python，另测9个坏状态；所有输入都是合成。

构建全部候选：`pio run`分别选择上述8环境（必须显式列出环境；不指定时仅构建default_envs）；然后`python3 collect.py --all`校验实际宏、源码哈希、镜像ID及HEX/DFU一致性。`collect.py`不带`--all`仍仅归档默认2k/4k。构建产物不是实物验收，硬件锁保持关闭。

收到R01后：确认电源/VCAP1/参考稳定并独立复核→测试源2k/4k→逐档SPI抓DRDY/CS/SCLK→固定速率30分钟无线采集。记录版本、环境、原始沿数、最短间隔、故障与丢样；不得仅凭软件计数放行。没有逻辑分析仪时，时序验收保持未测。

## IMU迭代后的构建

当前完整矩阵为原8档＋ads_2k_imu／ads_4k_imu，共10档。明确选择10档构建后再collect.py --all；来源检查同时绑定IMU宏、TIMER2相关SDK及SPI源码。默认2档归档入口不代表完整矩阵。IMU使用说明、协议与实物门见[IMU.md](IMU.md)。
