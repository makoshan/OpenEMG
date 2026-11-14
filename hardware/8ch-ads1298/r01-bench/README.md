# V12 R01：离体台架候选

**后续实板测试（2026-10-24）**　R01 在短接输入模式完成一次 10 分钟采集。上位机归档包含 91,368 个包、1,187,774 帧；重读归档后，帧序号连续，停止时的计数吻合。这次测试覆盖离体台架的数据传输。下面的设计交付记录保留了打样前的状态。

8通道ADS1298 + 外接XIAO nRF52840 Sense；65×60×1.6mm四层。原V12和F04保留。本版没有缩进佩戴主舱，也未放行人体连接或下单。

| 面板 | 当前内容 | 验收边界 |
|---|---|---|
| A 电路 | 208件，548个连接脚，原生KiCad 12页、S/Q与分组BOM | ERC与网表只证明文件一致；供电瞬态须实测 |
| B 封装 | 真实脚号、极性、Samtec/JST/Molex接口、自定义TI小封装 | 孔公差、器件批次、有效电容及实际压接未验 |
| C PCB | 8对输入按ADC针序，关键模拟/开关/去耦预先布线，内层1为地 | 最终检查见board-check.json；DRC不代替模拟性能 |
| D 固件 | F05真实ADS路径，19项主机正反例；2k/4k镜像互核 | 默认锁定、未刷机；IMU同步未实现 |
| E 文件包 | 导出脚本要求新跑原生DRC，并在解压后重跑 | 只有package-check.json成功记录才算导出完成 |
| F 实物 | [接口表](INTERFACES.md)、[离体验收表](BENCH-ACCEPTANCE.md) | XIAO/电池/线束、波形、噪声、无线和整圈装配仍开放 |

本地已实跑：208封装、1539段铜线、253过孔；原生DRC/未连/原理图一致性均零，577个实际焊盘逐一核网，过孔侵入SMD为零。

本地完成判据：`check_candidate.py`通过且6项负控拒绝；新跑原生ERC与PCB DRC/原理图一致性均零；`check_board.py`读取真实焊盘与铜通过；导出后解压重验通过。独立复核不得由这些数字替代。

复现顺序：`build_candidate.py` → `build_footprints.py` → `build_schematic.py` → `build_board.py` → `lock_references.py --placement` → 用现有Freerouting对DSN补线 → `finish_board.py` → 必要时`close_remaining.py`逐条补连 → `sync_board_metadata.py` → `check_board.py` → `export_review.py`。原生Python和CLI路径在脚本中显式记录；关键线随DSN保留fix/protect约束，补线不能擅自改动。生成器是初始布局入口；本版最终位置与手工出口调整以保存的原生PCB为准，重新生成不能覆盖已验收候选。

`V12-R01-REVIEW.zip`是可检查的完整候选，`V12-R01-GERBER-REVIEW-NOT-RELEASED.zip`只含制板层/钻孔。名称中的REVIEW表示尚有实物与工艺门；不要直接把候选当已放行制造版本。

审查证据在仓库`evidence/2026-10-04-v12-manufacturing-r01/`。此前失败路由、EP边缘相切负例及独立复核意见保留。原始资料和大构建产物仅本地保存，哈希随源码记录。

采购分组BOM含198件实体器件（195件SMD＋3件THT连接器）；10个裸铜测试点不采购。贴装坐标表仅含195件SMD，THT须单独安排插装；封装图形放在装配层，不能把装配层当丝印下单。
