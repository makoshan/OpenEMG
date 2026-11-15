# OpenEMG

[简体中文](README.md) · **English**

OpenEMG is an open-source **16-channel surface EMG wristband**. Our goal is to recognize hand gestures from muscle activity measured at the wrist. The desktop app displays waveforms, records labeled movements, and trains gesture models.

We want to do for EMG what DeepSeek did for AI: share the circuit, mechanical design, firmware, and desktop software so others can build a board and train a model on their own data.

We develop OpenEMG together with AI. It’s still early, and the circuits, code, and documentation will have mistakes. If you spot one, please [open an issue](https://github.com/makoshan/OpenEMG/issues). If you have a code fix, a circuit change, or measurements that tell a different story, [send a pull request](https://github.com/makoshan/OpenEMG/pulls) so others can build on your work.

[Status and roadmap](#status-and-roadmap) · [Gallery](#gallery) · [How it works](#how-it-works) · [Desktop app](#desktop-app)

| Front · U9 case and PCBs | Skin side · metal contacts |
|---|---|
| [![Long strap, clear case and short strap with buckle](hardware/16ch-afe-hirose-1mm-1nf/views/v001-wristband-iso-dark.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-wristband-iso-dark.png) | [![24 round contacts on the long strap, four on the short strap, and four round plus two square contacts under the case](hardware/16ch-afe-hirose-1mm-1nf/views/v001-wristband-skin-iso-dark.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-wristband-skin-iso-dark.png) |

The outside follows the R13 strap design. The skin side shows the dual 30-pin flex layout. The 24 round contacts on the long strap, four on the short strap and four under the case form 16 differential pairs. Two square auxiliary contacts sit under the case. A physical fit test is still pending. [Strap models](hardware/enclosure-46x40/c08b-shell-r13-notch/) · [Dual 30-pin electrode flex circuits](hardware/16ch-u9-dual30/strap-fpc-30p/)

**OpenEMG is in early development.** The November 15, 2026 PCB revision is ready for prototyping. Firmware, desktop integration, and gesture recognition are still in development. The 16-channel system has yet to be tested on hardware.

A 20-pin ribbon cable connects the six-layer controller board to the four-layer acquisition board. Two ADS1298 chips provide 16 differential inputs. [Design and fabrication files](hardware/16ch-afe-hirose-1mm-1nf/)

## Gallery

### Controller and acquisition PCBs

**PCB design is complete. Fabrication, assembly, and first power-on are next.** The acquisition board has 32 ESD protection diodes (D101–D132), one per input lead. The BOM and placement file cover 146 components.

| Board | Front | Back |
|---|---|---|
| C08B-U9 controller | [![C08B-U9 controller · Front](hardware/16ch-afe-hirose-1mm-1nf/views/v001-mcu-top.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-mcu-top.png) | [![C08B-U9 controller · Back](hardware/16ch-afe-hirose-1mm-1nf/views/v001-mcu-bottom.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-mcu-bottom.png) |
| 16-channel acquisition board | [![16-channel acquisition board · Front](hardware/16ch-afe-hirose-1mm-1nf/views/v001-afe-top.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-afe-top.png) | [![16-channel acquisition board · Back](hardware/16ch-afe-hirose-1mm-1nf/views/v001-afe-bottom.png)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-afe-bottom.png) |

The views come from the production Gerbers. The right column shows each board as seen from the back. [Board files](hardware/16ch-afe-hirose-1mm-1nf/) · [Controller with components](hardware/renders/v001-mcu-front.png) · [Acquisition board with components](hardware/renders/v001-afe-front.png)

### Mechanical assembly

| Controller above the acquisition board | Exploded view of the boards and U9 enclosure |
|---|---|
| ![Acquisition board visible through the controller's battery cutout](hardware/16ch-afe-hirose-1mm-1nf/views/v001-stack-iso-dark.png) | ![Cover, controller, acquisition board, and lower shell](hardware/16ch-afe-hirose-1mm-1nf/views/v001-exploded-iso-dark.png) |

These renders show the 0.8 mm bare-board configuration. The exploded view omits components, cable, and battery. Physical fit still needs testing. [Enclosure CAD](hardware/16ch-u9-dual30/enclosure-u9-watch/) · [Earlier enclosure and strap designs](hardware/renders/)

### Copper layers and schematics

| Controller · six layers | Acquisition board · four layers |
|---|---|
| ![Controller copper layers, top to bottom](hardware/16ch-afe-hirose-1mm-1nf/views/mcu-copper.png) | ![Acquisition board copper layers, top to bottom](hardware/16ch-afe-hirose-1mm-1nf/views/afe-copper.png) |

Read left to right, then top to bottom. All copper layers are viewed from above so you can follow traces through vias. [Controller Gerbers and drill files](hardware/16ch-afe-hirose-1mm-1nf/Gerber_C08B-U9_v0.01.zip) · [Acquisition Gerbers and drill files](hardware/16ch-afe-hirose-1mm-1nf/Gerber_AFE-30P.zip)

[![Schematic sheet 7: electrode inputs, filtering, and ESD protection](hardware/16ch-afe-hirose-1mm-1nf/views/schematic-afe-preview.png)](hardware/16ch-afe-hirose-1mm-1nf/views/schematic.pdf)

Sheets 1–5 cover controller power, Bluetooth, USB, inter-board connections, and the sampling MCU. Sheets 6–7 cover analog power, acquisition, electrode connectors, and input filters. [Searchable schematic PDF](hardware/16ch-afe-hirose-1mm-1nf/views/schematic.pdf) · [Editable EasyEDA Pro project](hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2)

| Assembly files | Controller | Acquisition board |
|---|---|---|
| Bill of materials | [Controller BOM](hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_bom.csv) | [Acquisition BOM](hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_bom.csv) |
| Pick-and-place coordinates | [Controller CPL](hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_cpl.csv) | [Acquisition CPL](hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_cpl.csv) |

This acquisition board is for off-body bench testing. Check board thickness, via-in-pad requirements, stencil details, and bottom-side orientation before ordering. [Fabrication notes](hardware/16ch-afe-hirose-1mm-1nf/) · [Safety before power-on or wear](SAFETY.md)

## How it works

A pinch produces small voltage changes at the skin. Each channel measures the voltage difference between two electrodes. Pairs at different positions see different waveforms from the same movement. The app saves waveforms alongside gesture labels so a model can learn to distinguish a pinch from rest.

[![System block diagram showing the electrodes, converters, controller and Bluetooth link](hardware/16ch-afe-hirose-1mm-1nf/views/v001-system-en.svg)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-system-en.svg)

[![Power tree showing USB charging, the battery and the digital and analog rails](hardware/16ch-afe-hirose-1mm-1nf/views/v001-power-en.svg)](hardware/16ch-afe-hirose-1mm-1nf/views/v001-power-en.svg)

[View the seven schematic sheets](hardware/16ch-afe-hirose-1mm-1nf/views/schematic.pdf)

Taking the band off and putting it back on changes electrode position and pressure. One four-channel study correctly classified 152 of 160 trials across four movements: making a fist, opening the hand, and flexing or extending the wrist. The paper does not say whether participants put the band on again before testing. We plan to train and test on separate wear sessions. [Research notes and paper](research/wrist-semg.md)

## Status and roadmap

**November 15, 2026.** The 16-channel v0.01 board design is ready for prototyping. The editable project, schematics, Gerbers, and assembly files are public. The firmware has passed host-side tests, and the desktop app can display 16 demo traces. **We have no measurements from this assembled system yet. The next milestone is a continuous bench recording of known signals on all 16 inputs.**

#### Before the boards arrive

| Work | What remains |
|---|---|
| Fabrication and assembly | Build from the November 15 package. Check board thickness, via-in-pad treatment, and stencil openings. Review both assembly sides for the two ADS1298 chips, three ribbon connectors, and 32 protection diodes. |
| Firmware adaptation | Check chip select, reset, clock, and bias settings against the final schematic. RLDIN connects to +2.5 V and the two chips have separate test pins. Review the earlier self-test configuration before using it on this revision. |
| Bench setup | Prepare the 20-pin cable, adapters, and an off-body signal source. Map the input pins to CH1–CH16 in the app and prepare shorted-input, known-signal, and stream-interruption tests. |

#### When the boards arrive: bench tests first

| Work | Evidence to collect |
|---|---|
| Inspection and power | Check component orientation, cable pin 1 at both ends, and continuity. Measure digital and analog rails, reference voltage, startup timing, and ripple. Test the acquisition power interlock with USB connected. |
| Board communication | Read the ID and registers of each ADS1298 separately. Observe both data-ready signals and verify the ordering of the two eight-channel groups. |
| Analog acquisition | Measure shorted-input noise on every channel, then inject a known signal into one input at a time. Record gain, polarity, mains interference, and adjacent-channel crosstalk. Test bias output with a simulated load. |
| Wireless link and desktop recording | Measure sample rate, dropped frames, and latency during a continuous hardware run. View, label, save, close, and replay a recording. Disconnect mid-run and check file integrity and whether the gap is visible. Run separate compatibility checks for 2 and 8 channels. |
| Enclosure, flex, and battery | Fit both boards and the cell. Insert the 20-pin cable and both 30-pin flex tails. Check latch access and cable clearance with the lid closed. Measure power draw, temperature rise, and runtime. |

#### After bench validation: wear and gesture tests

| Work | Evidence to collect |
|---|---|
| Before wear | Review electrode connections, current-limiting paths, battery power, and the charging interlock before scheduling wear tests. [Safety notes](SAFETY.md) |
| Electrode contact and data | Record band position and tightness. Compare each channel at rest, during movement, and after refitting. Keep gesture labels and wear-session IDs so intermittent contact can be traced. |
| Gesture recognition | Start with rest, activation, and four swipe directions. Train on one wear session and test on another. Report results per gesture, response time, and false triggers at rest. |
| Reproducing a build | Publish assembly photos, firmware versions, desktop connection instructions, and first-board measurements. Have another developer follow the public files through assembly and recording and document where they get stuck. |

### Desktop app

![OpenEMG demo showing all 16 EMG traces and the per-channel RMS ring](app/screenshots/studio-16ch-demo.png)

The screenshot uses demo data. It shows all 16 waveforms on the left. Each segment of the ring on the right shows one channel’s root mean square (RMS) amplitude in µV.

View waveforms, record movements, and train gesture models. [App source](app/)

### Hardware variants

| Channels | Design and firmware | Mechanics | Status |
|---|---|---|---|
| **16** | [Dual Hirose 30-pin](hardware/16ch-u9-dual30/), [v0.01 Hirose 1 nF](hardware/16ch-afe-hirose-1mm-1nf/), [dual XUNPU 30-pin](hardware/16ch-afe-xunpu-2mm-1nf/), [dual 34-pin](hardware/16ch-c08b-round/). [Controller self-test](firmware/c08b-bringup/) · [Dual ADS1298 firmware](firmware/c08b-stream/) | [U9 enclosure](hardware/16ch-u9-dual30/enclosure-u9-watch/) | Priority build. Hirose assembly checked in CAD. Fabrication and 16-channel bench testing are next. The XUNPU variant has a separate [bias circuit review](hardware/16ch-afe-xunpu-2mm-1nf/#待工程师确认). |
| **8** | [D20 wristband](hardware/8ch-ads1298/afe-d20-8ch/), [R01 bench board](hardware/8ch-ads1298/r01-bench/). [Wristband firmware](firmware/c08b-stream/) · [R01 Bluetooth firmware](hardware/8ch-ads1298/r01-bench/firmware-f05-ble-dout/) | [R12 enclosure](hardware/enclosure-46x40/c08b-shell-r12/) · [D2 electrode flex](hardware/8ch-ads1298/strap-fpc-d2-8ch/) | R01 recorded 1,187,774 consecutive frames in 10 minutes with shorted inputs. The D20 wristband still needs an assembled test. |
| **2** | [ADS1292 six-contact board](hardware/2ch-ads1292/) · [XIAO Bluetooth firmware](firmware/xiao-ads1292-2ch/) | [R7 enclosure](hardware/enclosure-46x40/ads1292-shell-r7/) | Design checked. Fabrication and power-on pending. |

## Getting started

[Desktop app](app/) · [Development environment](firmware/software.md) · [Hardware index](hardware/README.md) · [Safety notes](SAFETY.md)

[Software license (MIT)](LICENSE) · [Hardware license (CERN-OHL-S-2.0)](LICENSE-HARDWARE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
