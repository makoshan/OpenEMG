# F05 离体台架豁免版

2026-10-21 Mako 批准方案 B：不实测 VCAP1 和参考稳定时间，用保守的等待时间放行 F05。**只用于离体芯片内部测试，不上人体。**

| 项 | 值 | 依据 |
|---|---|---|
| POR 等待 | 5 s | 数据手册最小 131.3 ms，未实测 |
| 参考稳定等待 | 1 s | 未实测 |
| 元数据 | `bench_measured:true` 加 `bench_basis:"waived_by_Mako_2026-10-21_not_measured"` | 归档时据此区分“豁免”和“实测” |
| 本地清单 profile | `F05_ADS_BENCH_WAIVED` | 只出现在 artifacts/ 的清单 JSON 里 |
| 上机后怎么认 | 看 BLE 元数据里的 `bench_basis` | 原版和豁免版经 BLE 发出的 profile 都是 `F05_ADS_CANDIDATE`；主机只认这个名字，所以不能改 |

放行前已有的实物证据：P03 万用表版在电池供电下把整套上电和复位序列跑完，没有报故障。这表示固件粗筛通过：AVDD 在 4.6–5.4V 之间，D5（OE_N）为低。VCAP1、DVDD、参考电压都没有实测。

## 为什么单独建一个目录

`firmware-f05` 一个字节都不改。原因有三：

- C05P 和 F05C 都直接引用 F05 的 `src` 目录，其中 F05C 还写了 `MAKO_BENCH_MEASURED != 0` 就报错。
- C05P 钉死了 F05 `main.cpp` 的哈希。
- CI 禁止 F05 有任何改动。

所以由 `build.py` 在 `.pio/stage` 里复制一份 F05，只在副本里替换 `bench_release.h`、补上元数据。复制进副本的全部 F05 文件（3 个工程文件和 `src/*`，包括 `ads1298.cpp` 里的锁门和等待逻辑）合起来钉一个哈希。其中任何一个文件变了，脚本都会直接停下，要重新审查补丁后再更新哈希。脚本还会解析要烧录的 hex，确认豁免标注确实在会烧进芯片的数据里。

## 构建

```
python build.py --env ads_2k --pio <pio 路径> [--toolchain platformio/toolchain-gccarmnoneeabi@1.120301.0]
```

本机全局的 pio 和 7.2.1 工具链是 x86 版，所以要加 `--toolchain` 换成原生 arm64 的 GCC 12.3.1。这个参数只影响副本里的 `platformio.ini`。换了 GCC 版本，镜像用的工具链就和 F05 原清单记录的不一样了，这一点会写进清单 JSON。镜像和清单 JSON 只留在本地 `artifacts/` 里。

## 使用注意

- 启动一次大约要 6 秒（5 s + 1 s + 电源稳定检查）。主机采集要用 `--seconds 15` 或更长；默认的 5 秒会在出第一个样本之前就超时并发出 STOP。
- `host/v12_ble.py` 目前不校验、也不保存 `bench_basis`。要判断某段数据是不是豁免版采的，只能看原始 meta。
- 以后补测了 VCAP1 和参考电压，就改回实测值，不再使用这个目录。

已核：`test_ads1298` 25 项（2026-10-22 ID 判断放宽后为 30 项）、`check_v12_ble` 32 组、`check_v12_status`、`check_c05p_fw`、`check_f05c` 全部通过。哈希变化时脚本能拦住（反例已验证）。
