# F04独立只读复核

2026-10-03，复核者：独立会话`dsp_review`。范围为firmware-f04代码与固定Seeed SDK；未改仓库、未操作设备。最终main SHA256为36ab37054c814bdd170cea1ccc9764d918c5ec6a78283ac400b65c38d3827f28。

## 发现与关闭

- **P1应用连接悬空**：旧main保存BLEConnection指针后生成最多32帧。BLE高优先级任务删除对象，异步disconnect回调可能尚未执行，epoch不能挡住后续getMtu/notify。改为同步setEventCallback留代次/MTU数值，短暂停任务切换，直接SoftDevice非阻塞完整提交；宿主同句柄重连检查通过。
- **P1 SDK内部悬空**：真实bluefruit.cpp断连分支删除数组指针，却未清局部conn，随后Periph/Central角色分发解引用。精确哈希补丁仅在本项目生成副本加conn=NULL；两环境副本逐字相等、共享SDK哈希不变。原分支存活标记探针退出2，修复副本退出0。Periph/Central的断连分支均空，未发现清指针导致新增动作。

## 独立执行

普通/UBSan临时探针核2/4k队列：满队列丢新32帧、重试字节相同，收到129帧且missing=32；调度缺20帧拆包，missing=20；MTU46/185/247/517容量1/6/8/8。

读取真实main并链接真实stream/codec/dsp，仅Arduino/Bluefruit/SoftDevice为替身。2/4k通过：GPIO先LOW再OUTPUT，NRF_ERROR_RESOURCES不提交且重试同字节；100ms停顿只生成32帧、分别跳过168/368帧；快照后断连再同句柄连接，旧轮不发送、新会话序号0及SESSION_START。

真实main编译AFE_ENABLED=1及fs=1000分别退出1，命中对应#error。复核时最终build.log显示两环境编译generated/bluefruit.cpp.o并链接成功。ELF未作指令级验收。

复现源码已由实现会话复制到main-check，命令为`python3 emg/v12/firmware-f04/main-check/run.py`；日志main-check.log、main-check/negative-compiles.json。复制后本机会话又跑通过；独立复核依据仍为原会话报告与同一main源码哈希。

## 结论与边界

在上述代码范围未发现未关闭P0/P1。**发送成功仅表示SoftDevice已入队。** Mac接收、实际BLE吞吐/重连、真实RTOS并发、GPIO波形、冷启动/掉电、电平转换、AFE/ADC与人体安全均未实测。整机电气P0保持开放；本复核不能签制造或佩戴验收。
