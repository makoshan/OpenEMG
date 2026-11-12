# platform 固定样本

- `windows.json`：60 个真实手势特征窗（circle / up_wave / punch / other 各 15），来自手表固件仓 `gesture-data-4s/`，
  用 `separability.features` 算的 12 个物理特征。**只有特征离开了固件仓，没有原始样本、没有 BLE 地址。**
  重新生成：在固件目录 `PYTHONPATH=. .venv-gesture/bin/python <site>/platform/tools/export_fixture.py gesture-data-4s 15 > <site>/fixtures/platform/windows.json`
- 坏样本不单独存文件：`scripts/check-platform.mjs` 在跑的时候现场构造（带 raw_adc 的事件、丢帧 31% 的会话、夹带 waveform 的特征窗、`--tamper` 的回放）。
