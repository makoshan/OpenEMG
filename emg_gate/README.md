# EMG Gate · P0 + P1 Implementation

**面向单通道 ADS1292 的肌电采集协议 + 本地自校准三档闸门**

依据：
- `ADR-2026-09-23-EMG软件采集训练个性化.md` v0.1
- `ADR-2026-09-23-sEMG处理链.md` v0.1.1
- `CTO-DEC-2026-09-23-EMG软件优先阶段.md`

## 范围

### P0 — 采集协议（已实现）
- `CaptureSession` 完整 schema 与验证
- 封闭手势枚举：`rest | light | hard | lead_off_neg | confirm_pulse`
- 质量门控：`lead_off`/`poor_contact`/`clip` 等
- 本地缓存 + 导出；默认不含 raw；`CloudSafeEvent` 强制无 raw
- 协议验收清单

### P1 — DSP + 自校准闸门（已实现）
- DSP 链：`raw → DC → HPF≈20Hz → 条件50Hz陷波 → 整流 → 包络(RMS/MA) → 三档`
- 质量门：劣质信号强制 `band=0`、低置信、不假绿
- `CalibrationProfile` 本地自校准：采样 rest/light/hard → 定阈值 → 验证松脱负样
- CLI 支持完整采集 / 校准 / 导出 / 验收清单工作流

### 晚融合 — IMU 动作 × 肌电用力（本地判定，不训练）
- 一个主机时钟窗：`imu.motion` 与 `emg` 的 RMS 档位分开写，没有单一 `gesture_label`
- 力量只认闸门的 RMS 档（休息 / 轻 / 重）。IMU 的 12 个特征不进入这个数
- 松脱、接触差、削顶的窗不报力量。有动作且肌电在休息档，也不报力量
- `still` / `daily` 导出成 IMU 训练标签 `other`；`hook` / `uppercut` 默认不并进 `punch`
- 五类（放松、捏合、搓动、响指、握拳）拒收 `rest|light|hard|lead_off_neg|confirm_pulse`
- 契约：`schemas/paired_window.schema.json`。命令：`python3 -m emg_gate.cli fuse`
- `split` 把一次录音拆成三份：IMU 快照（动作标签 + 12 特征）、力度校准行、五类行。配对窗只追加 IMU 行和判定，不写入力度集或五类集。`track=joint` 直接拒绝。力度不在这里拟合模型。默认 IMU 类是 `circle up_wave punch other`，每类两场会话才算可以接着训
- `split --fixture fixtures/platform/windows.json` 把手表的 `split=test` 留在独立测试里。这份夹具训练场次不够（画圈、上挥各 1 场，其它 0 场），`--require-ready` 退出码 1。不把这些窗改成力度标签

### 数据公地 — 同一硬件的共享数据与共享模型（本地机制 + 门禁）
- `commons bundle`：本机 pack → 去标识贡献包（无 user_id / device_id / 会话 id / 绝对时间；随机假名；raw 要单独同意）
- `commons verify / contribute / withdraw`：从文件重算哈希和计数；按硬件 `pool_key` 和许可收包；哈希链账本；凭本机密钥撤回，撤回让相关快照和模型作废
- `commons snapshot / train / gate / release`：先隔离标签不成序的人，再按**人**分训练/测试；门禁重训复现参数，留出人最差准确率 ≥ 下限且 false_green=0
- 去中心化：Ed25519 签名（纯 Python，`ed25519.py`）；`commons merge --from <另一副本>` 交换包、撤回、评测声明并逐个重验；同样的数据在任何副本上得到同样的快照和模型 id
- 你自己的数据：`commons personalize` 用共享模型当先验、在你自己的留出数据上挑出专属阈值（不出本机）；`commons attest` 本机评测后只签名公布数字，`commons scoreboard` 汇总有支撑、独立的声明
- 许可与传输（2026-09-30 定）：数据 CDLA-Permissive-2.0；副本之间用 git 交换仓。`commons git-sync --root <副本> --repo <共享仓库克隆>` 拉取→导入→导出→`verify-repo`→提交，加 `--push` 才推送；`commons verify-repo` 可放进共享仓库的 CI
- 共享阈值默认是「每人各自拟合 → 取中位数」（一人一票，少于一半的人作假带不偏）；`commons train --method pooled` 是混合拟合对照
- 贡献者一条命令：`commons share --pack <包> --hardware <指纹> --root <本机副本> --repo <共享仓库克隆> [--push]`
- 一条命令跑通：`python3 -m emg_gate.cli commons-demo --root /tmp/c --work /tmp/cw --poisoned 1`（合成数据，结果盖 `evidence_grade=synthetic`）
- 不含上传或托管；下面的 NO-GO 仍然有效

### NO-GO（明确不含）
- P2 云端 Generic 训练 / 权重下发
- P3 端上 DNN / fine-tune 训练闭环
- 云上传代码；raw 默认上云
- 多通道假设（单通道 ADS1292）

## 安装

```bash
cd /workspace/emg
pip install -e .
# 或使用 uvx（推荐）
```

## 快速开始

```bash
cd emg
python3 -m unittest discover -s emg_gate/tests -p "test_*.py" -v
```

### 1. P0 采集：session pack（本地落盘）

```bash
P=/tmp/pack
python3 -m emg_gate.cli session --pack $P create --user u1 --device ads1292_a
python3 -m emg_gate.cli session --pack $P don                       # 贴电极 → 新 donning_id
python3 -m emg_gate.cli session --pack $P new --session-id s1 --posture sit
python3 -m emg_gate.cli session --pack $P append --session s1 --gesture rest  --quality ok --norm 0.05 --band 0
python3 -m emg_gate.cli session --pack $P append --session s1 --gesture light --quality lead_off --norm 0.3   # REJECTED（正类+lead_off），不落盘
python3 -m emg_gate.cli session --pack $P doff                      # 摘电极
python3 -m emg_gate.cli session --pack $P new --session-id s2       # REJECTED：必须先 don
python3 -m emg_gate.cli session --pack $P don && python3 -m emg_gate.cli session --pack $P new --session-id s2 --held-out
python3 -m emg_gate.cli session --pack $P mark-held-out --session s2
```

一条命令生成完整合成 pack（2 次 donning，最后一次 `held_out`，4 档）：

```bash
python3 -m emg_gate.cli session --pack /tmp/pack_demo demo-pack --seconds 160
```

### 2. 导出 / 上云信封

```bash
python3 -m emg_gate.cli export --pack /tmp/pack_demo --out /tmp/a.jsonl                 # 默认剥 raw；可复现（sha256）
python3 -m emg_gate.cli export --pack /tmp/pack_demo --out /tmp/dev.jsonl --include-raw   # 开发者，仅本地
python3 -m emg_gate.cli cloud-safe-export --pack /tmp/pack_demo --out /tmp/cloud.jsonl    # 每行过 CloudSafeEvent schema
```

### 3. P0 验收清单（sat / unsat 逐项 + 数字）

```bash
python3 -m emg_gate.cli checklist --pack /tmp/pack_demo            # ADR 门槛 120 s/档；exit 0 = PASS
python3 -m emg_gate.cli checklist --pack /tmp/pack_demo --min-seconds 10   # 放宽时报告会明示「不构成正式过线」
```

### 4. P1 校准 / 回滚 / smoke

```bash
python3 -m emg_gate.cli calibrate --out /tmp/p/active.json --from-pack /tmp/pack_demo --eval-out /tmp/eval.json
#   held_out 窗不进拟合；commit 后单独评估 held_out 出 FP/FN/false_green
python3 -m emg_gate.cli calibrate --out /tmp/p/active.json --seed 99     # 再 commit：旧表归档到 profile_store/，写 prev_profile_ref
python3 -m emg_gate.cli calibrate --out /tmp/p/active.json --rollback    # 恢复上一张；被弃的标 stale=true 归档
python3 -m emg_gate.cli authorize-smoke --profile /tmp/p/active.json     # 三档可分 + lead_off/poor_contact/clip 零 authorize
```

### 5. 只跑信号链

```bash
python3 -m emg_gate.cli run --scenario all --out /tmp/run
```

## 目录结构

```
emg/
├── README.md                          # 本文件
├── pyproject.toml                     # 包定义
├── requirements.txt                   # numpy-only 依赖
└── emg_gate/                          # Python 包
    ├── __init__.py
    ├── cli.py                         # CLI 入口
    ├── capture_session.py             # P0 CaptureSession schema
    ├── calibration_profile.py         # P1 CalibrationProfile schema
    ├── cloud_safe_event.py            # CloudSafeEvent（拒 raw）
    ├── session_store.py               # P0 session pack：don/doff、拒收前不落盘、可复现导出
    ├── demo_pack.py                   # 合成 pack 构造器（含必失败样本开关）
    ├── checklist.py                   # P0 验收清单（时长 / 重戴 / held_out / 导出复现）
    ├── calibrate.py                   # 自校准、held_out 排除+评估、commit_profile、rollback
    ├── smoke.py                       # authorize-smoke
    ├── filters.py                     # DSP 链（port from demo）
    ├── quality.py                     # 质量检测 + flags↔label
    ├── gate.py                        # 三档闸门逻辑
    ├── fusion.py                      # IMU 动作 × RMS 用力；不训练
    ├── split_tracks.py                # 一次录音拆成 IMU / 力度 / 五类
    ├── commons_bundle.py              # 数据公地：硬件指纹、去标识贡献包、verify
    ├── commons_ledger.py              # 数据公地：哈希链账本、撤回、按人快照
    ├── commons_model.py               # 数据公地：共享阈值、门禁、发布
    ├── commons_demo.py                # 数据公地：合成端到端
    ├── commons_attest.py              # 数据公地：本机评测声明（签名）
    ├── ed25519.py                     # RFC 8032 签名，纯 Python
    ├── commons_git.py                 # 数据公地：git 交换仓（export / verify-repo / git-sync）
    ├── licenses/                      # 交换仓要带的数据许可原文（CDLA-Permissive-2.0）
    ├── jsonlite.py                    # JSON Schema 子集校验（numpy-only 下不装 jsonschema）
    ├── pipeline.py                    # 完整管线
    ├── synth.py                       # 合成数据生成
    ├── schemas/                       # JSON Schema（Python 校验的白名单/必填集从这里派生）
    │   ├── capture_session.schema.json
    │   ├── calibration_profile.schema.json
    │   ├── cloud_safe_event.schema.json
    │   ├── paired_window.schema.json
    │   ├── hardware_profile.schema.json
    │   ├── commons_manifest.schema.json
    │   ├── commons_row.schema.json
    │   ├── commons_model_card.schema.json
    │   └── commons_attestation.schema.json
    ├── configs/
    │   └── default_thresholds.json
    ├── tests/                         # unittest；jsonschema 可选交叉验证
    └── evidence/                      # 运行证据（大 pack / 全量导出不入库）
```

## 核心概念

### CaptureSession（P0 采集对象）

```python
{
  "schema_version": "1.0.0",
  "user_id": "user_abc",
  "device_id": "ads1292_001",
  "session_id": "sess_20260923_001",
  "donning_id": "don_001",              # 每次重戴必换
  "gesture_label": "rest",              # rest|light|hard|lead_off_neg|confirm_pulse
  "obs_ts_device_ms": 1234567890,
  "obs_ts_host_ms": 1234567891,
  "fs_hz": 500.0,
  "window_ms": 200.0,
  "payload_kind": "feature_window",
  "feature_window": { "band": 0, "norm": 0.08, ... },
  "quality": {
    "lead_off": false,
    "poor_contact": false,
    "line_noise": false,
    "clip": false,
    "artifact_suspect": false
  },
  "held_out": false
}
```

**拒收规则**：
- 缺必填字段（`donning_id`, `gesture_label`, 双时间戳, `quality`）
- 正类手势（rest/light/hard）但 `lead_off=true` 或 `clip=true`

### CalibrationProfile（P1 本地校准表）

```python
{
  "schema_version": "1.0.0",
  "user_id": "user_abc",
  "device_id": "ads1292_001",
  "donning_id": "don_001",             # 可选：特定佩戴
  "chain_ver": "1.0.0",
  "thresholds": {
    "th_loose_max": 0.12,
    "th_hard_min": 0.38
  },
  "created_at": "2026-09-23T12:00:00Z",
  "stale": false,
  "prev_profile_ref": null             # 支持回滚
}
```

### CloudSafeEvent（上云白名单，拒 raw）

```python
{
  "schema_version": "1.0.0",
  "kind": "band_change",
  "band": 1,
  "quality": "ok",
  "confidence": 0.75,
  "t_host_ms": 1234567890,
  "summary": "轻用力"
  # 无 raw_window, raw_adc, raw_uV 字段
}
```

## 验收清单（P0 acceptance）

`python3 -m emg_gate.cli checklist --pack <dir>` 逐项给 sat / unsat 与背后的数字：

| 项 | 判定依据 |
|---|---|
| 新会话有 `session_id` + `donning_id` | 每个 session meta 都有；每一窗过白名单 schema |
| 摘戴后重开有新 `donning_id` | pack 里 ≥2 个 donning，且前一个在下一个开始前已 `doff` |
| 三档 + `lead_off_neg` 采满时长 | **非 held_out** 的合格窗（正类无任何 quality 标志；负样 lead_off=true）区间并集 ≥ `--min-seconds`（ADR 默认 120） |
| 可标记 `held_out` | ≥1 个 held_out 会话且其窗已带标记 |
| 导出可复现、默认无 raw | 连导两次 sha256 相同；默认导出零 `raw_window` |

必失败样本（测试与 CI 都有）：20 s pack @120 s → FAIL；`--omit-lead-off-neg` → FAIL；`--donnings 1` → FAIL；篡改一窗加自由文本字段 → FAIL。

## 技术栈

- **Python 3.8+**，**numpy only**（无 scipy；已实现 biquad IIR）
- **JSON Schema**（`schemas/`）是契约真源；Python 校验器的白名单 / 必填集从它派生，装有 `jsonschema` 时测试会交叉验证
- **unittest**（无 pytest 依赖）

## 证据文件

- `emg_gate/evidence/followup-2026-09-26/`：checklist 正样本 + 3 个必失败样本、拒收输出、导出 hash、校准 / rollback / smoke 输出、profile JSON
- `emg_gate/evidence/emg-p0p1-2026-09-23.md`：PR #27 时的证据（顶部有更正说明）

## 限制与边界

1. **单通道**：假设 ADS1292；不支持 Meta 多通道
2. **本地 only**：无云上传代码；`raw` 默认不导出
3. **传统特征**：包络 + 阈值；无 DNN
4. **自校准 ≠ 训练台**：仅本机简单采样定阈值
5. **质量优先**：劣质信号不假绿
6. **晚融合不改三档**：不拼 IMU 特征，不把力度标签改成五类，不升采样率，不上白化

## 开发

```bash
pip install -e .            # 提供 `emg-gate` 命令（等价于 python3 -m emg_gate.cli）
python3 -m unittest discover -s emg_gate/tests -p "test_*.py" -v
```

CI：`.github/workflows/ci.yml` 自动执行 `emg_gate/tests` 下全部 170 项单元测试。

## 许可

MIT License（详见仓库根目录 [LICENSE](../LICENSE)）。
