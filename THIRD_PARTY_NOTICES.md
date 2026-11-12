# 第三方组件与外部资料声明（Third-Party Notices）

本仓库按模块采用双层开源许可：
- `hardware/` 下的全部原理图、KiCad 工程、嘉立创 EDA 工程（`.epro2` / `.epcb2`）、制造文件与 3D 结构：**CERN-OHL-S-2.0**（见 [LICENSE-HARDWARE](LICENSE-HARDWARE)）
- `app/`、`apple/`、`host/`、`emg_gate/`、`firmware/`、`game/`、`duck/`、`tools/`、`scripts/` 下的软件与固件源码：**MIT License**（见 [LICENSE](LICENSE)）

---

## 随仓包含的第三方开源资源

1. **Three.js (v0.186.0)**
   - 位置：`game/tianjie/`（源码）与 `app/game/tianjie/`（桌面端静态挂载包）
   - 许可证：MIT License（全文见 [three-LICENSE.txt](app/game/tianjie/assets/three-LICENSE.txt)）

2. **WebXR Input Profiles Generic Hand (`hand-right.glb`)**
   - 来源：`immersive-web/webxr-input-profiles` (Amazon, 2019)
   - 位置：`app/game/tianjie/assets/hand-right.glb`
   - 许可证：MIT License（全文见 [hand-LICENSE.txt](app/game/tianjie/assets/hand-LICENSE.txt)）

3. **Poly Haven 环境材质贴图（`cobblestone_floor_001`、`rock_boulder_dry`）**
   - 位置：`app/game/tianjie/assets/floor-*.jpg`、`rock-*.jpg`
   - 许可证：CC0 1.0 Public Domain Dedication

4. **CDLA-Permissive-2.0 协议模板文本**
   - 位置：[CDLA-Permissive-2.0.txt](emg_gate/licenses/CDLA-Permissive-2.0.txt)
   - 用途：供社区共享匿名特征集时选用的开放数据协议文本参考。

---

## 硬件设计参考芯片手册

- Texas Instruments *ADS1298 / ADS1298R Low-Power, 8-Channel, 24-Bit Analog Front-End for Biopotential Measurements* (SBAS459K), *ADS1292 Low-Power, 2-Channel, 24-Bit Analog Front-End* (SBAS502C) & *Improving Common-Mode Rejection Using the Right-Leg Drive Amplifier* (SBAA188)
- STMicroelectronics *STM32L432KC Datasheet* (DS11451) & *AN2606 STM32 Microcontroller System Memory Boot Mode*
- Nordic Semiconductor *nRF52840 Product Specification*
