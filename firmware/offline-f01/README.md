# F01：便携协议候选与离线接收检查

2026-10-02。状态：已实现未验收。只在Mac上用合成输入编译/测试，没有nRF52840目标固件、SPI/DRDY、BLE或电气安全验收。该协议是OVERALL_PLAN §5的16字节头+27字节ADS帧的具体候选；未签署冻结，没有改现有固件或App。

## 字节契约（候选实验版1）

| 偏移/长度 | 字段 | 格式 |
|---|---|---|
| 0/1 | version | 1 |
| 1/1 | type | 1=ADS；IMU布局/量程/单位未定，其他类型拒绝 |
| 2/1 | count | 1..8，且不超过协商MTU容量 |
| 3/1 | flags | bit0合成输入，bit1新会话；其他位拒绝 |
| 4/4 | sequence | uint32小端，首帧采样序号；每个ADC帧递增，允许回卷 |
| 8/8 | timestamp_us | uint64小端，首帧设备单调时钟微秒；非电脑墙钟 |
| 16/27×count | frames | 每帧3字节原始状态+8×3字节二补码、大端通道；原始值保留 |

这不是电极逻辑脚号格式；通道按ADS IN1..IN8，不把P/N当电源正负。没有把ADC码换算成电压或肌肉位置；量程、参考、增益和IMU配置须在实际固件/数据记录中冻结。

ATT载荷最多MTU−3字节：247装8帧=232字节；185装6帧=178字节；23连一帧都不支持，明确报错，不静默截断或伪造缺失数据。未实现分片或批大小自动回退。数据损坏可能改变一个仍合法的采样值；本候选无端到端CRC，坏包检查不能宣称覆盖所有位错误。

新连接须SESSION_START且序号0；接收器已连接时不允许静默重启，先记录disconnect。timestamp检查只保证包首时间单调，不证明2kSPS真实时钟、跨包采样连续或IMU同步。接收器缺省拒绝实测来源，调用方只有明确配置allow_real才能接收；不能把标志作为真实性认证。合成与真实不能在一个会话混用。

序号前向缺口按采样帧数计missing_samples，不补造样本；半圈或更大的回卷差按乱序/重复拒绝。设备复位、超长断连须建立新会话，不能从序号猜测。bad包不推进expected；接收计数不包含被拒包。未实现实时BLE队列/环形缓冲或ADC溢出计数，这些是目标固件工作。

## 文件与检查

- codec.py：主机参考编解码、24位解析、序号/错误计数。
- v12_codec.h/.c：无堆分配的C99协议代码，可移植候选；v12_decode返回帧指针借用输入内存，调用者必须保存数据寿命；encode输入帧和输出缓冲不应重叠。不是nRF驱动。
- host_probe.c/check.py：实际clang编译、独立手写黄金字节和正负输入，C/Python互操作。测试夹具全部合成，未调用任何设备。
- results.json/check.log：本轮实际结果/源码哈希。
- sanitizer-first-failed.log：ASan/UBSan组合探针在Mac上超时，本轮单个probe被终止。旧失败保留；恢复后最小空main在ASan/组合模式仍5秒超时，UBSan可运行。完整协议检查已在UBSan（不可恢复错误）及普通C99模式下分别通过，ASan仍未通过；见sanitizer-diagnostic.json和results-ubsan.json。

从项目根执行：`PYTHONDONTWRITEBYTECODE=1 python3 firmware/offline-f01/check.py`。编译和探针都有明确超时，临时二进制只放临时目录。完整UBSan重试：`PYTHONDONTWRITEBYTECODE=1 python3 firmware/offline-f01/check.py --sanitizer undefined`。诊断：`PYTHONDONTWRITEBYTECODE=1 python3 firmware/offline-f01/sanitizer_diagnostic.py`；只输出有关Sanitizer变量是否存在，不读取凭据。

## F01仍阻塞的部分

本项目未找到V12的.ino/platformio.ini/west.yml/CMake固件目标工程；arduino-cli和west当前不可用。需要核XIAO Sense实物修订、目标SDK/板包、实际J1引脚与IMU内部/外部I²C，才能可靠跨编译与实施采集。不同现有手表固件不能当作此板目标。

P0-3要硬件默认态、固件状态机与实测共同关闭：根据electrical-e01，最坏tPOR约131.3ms，另有VCAP1条件和时钟/复位要求。没有VCAP测量/监测路径与电源状态波形，不能只写延时就声称安全。当前包解析与序号测试不控制ANA_EN/PWDN/OE，不改变该阻塞。

下一步由固件执行者核目标和引脚后集成便携模块，冻结帧契约/元数据，编译目标固件，再在离体台架运行F02/B01/S01；独立复核后才考虑H01。

## 2026-10-02：便携C接收状态机已实现

v12_receiver.h/.c补齐Python Receiver既有行为：首包会话、来源隔离、32位序号回卷、缺失计数、乱序/重复拒绝、时间戳单调及显式断连。拒绝不推进采样/会话状态；malformed/reordered诊断计数允许增加。累计计数为uint64，不重置；disconnect仅清连接状态。单调用者串行使用，调用者负责线程同步及超长运行计数溢出策略。成功out借用输入包内存，调用者须保留其寿命。

receiver_probe.c/receiver_check.py将521次包处理逐步对照Python的10项状态字段，普通与UBSan、allow_real开关共4组2084次全部一致；乱序和时间戳检查删除反例均被检出。全部输入仍为合成，即使allow_real=True也不代表有真实采集。

命令：`PYTHONDONTWRITEBYTECODE=1 python3 firmware/offline-f01/receiver_check.py`。结果receiver-results.json、receiver-check.log。检查退出0只表示主机差分检查通过；ARM结果单独读取arm_objects。

已发现arm-none-eabi-gcc。新receiver在Cortex-M4 freestanding模式编译为对象成功；现有codec因工具链缺string.h失败（receiver-first-arm-failed.log保留原失败）。未安装/猜定SDK、板包或引脚，未链接目标固件。该新增库尚未接到BLE回调或目标工程，不关闭F01/F02/B01/P0-3。
