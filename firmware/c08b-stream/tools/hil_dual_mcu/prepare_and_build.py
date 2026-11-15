#!/usr/bin/env python3
"""从 firmware/c08b-stream 同步最新源码到树外临时目录，构建 STM32L432KBU6 (128KB + C08B_SWD_HIL 128槽) 与 XIAO nRF52840 UF2。"""
from pathlib import Path
import shutil
import struct
import subprocess

import os
import tempfile

HERE = Path(__file__).resolve().parent
SRC_FW = HERE.parents[1]  # firmware/c08b-stream
WORK_ROOT = Path(os.environ.get("C08B_HIL_WORKDIR", Path(tempfile.gettempdir()) / "c08b-dual-hil"))
FW_DIR = WORK_ROOT / "c08b-stream-hil"
for sub in ("common", "l432", "nrf", "host_test", "tools"):
    (FW_DIR / sub).mkdir(parents=True, exist_ok=True)
for extra in ("Makefile", "common/bench_release.h", "common/rtt.h", "common/baremetal_stubs.h", "l432/pins.h", "nrf/pins.h", "nrf/nrf52840_nosd.ld"):
    if (SRC_FW / extra).exists():
        shutil.copy2(SRC_FW / extra, FW_DIR / extra)

# 0. 从唯一最新源码仓同步协议头与双核源码（保持 MAKO_C08B_AFE_ENABLED=0, MAKO_BENCH_MEASURED=0）
for rel in [
    "common/stream_proto.h",
    "l432/main.c",
    "l432/l432.ld",
    "nrf/main.c",
    "nrf/nrf52840_s140.ld",
    "host_test/test_stream_host.c",
]:
    shutil.copy2(SRC_FW / rel, FW_DIR / rel)

# 1. 适配 STM32L432KBU6 (128KB Flash, 48KB SRAM1)
ld_path = FW_DIR / "l432/l432.ld"
ld_path.write_text(ld_path.read_text().replace("LENGTH = 256K", "LENGTH = 128K"))

# 2. 在 l432/main.c 注入非侵入式 C08B_SWD_HIL 128 槽 BSS 环形邮箱（当物理 PB6=LINK_RDY 拉高时仍优先走原生 8MHz SPI3）
main_c = FW_DIR / "l432/main.c"
src = main_c.read_text()

hil_decl = """/* 供 SWD 调试器直接观察的全局遥测快照 */
volatile c08b_link_tx_t g_tx_frame;
volatile c08b_link_rx_t g_last_rx;

#ifdef C08B_SWD_HIL
#define C08B_HIL_SLOTS 128u
typedef struct {
    uint32_t       magic;
    uint32_t       enable;
    uint32_t       tx_head;
    uint32_t       tx_tail;
    uint32_t       rx_seq_wr;
    uint32_t       rx_seq_ack;
    c08b_link_rx_t rx_slot;
    c08b_link_tx_t tx_ring[C08B_HIL_SLOTS];
} c08b_swd_hil_t;

__attribute__((used)) volatile c08b_swd_hil_t g_swd_hil;
#endif"""

old_decl = """/* 供 SWD 调试器直接观察的全局遥测快照 */
volatile c08b_link_tx_t g_tx_frame;
volatile c08b_link_rx_t g_last_rx;"""
assert old_decl in src, "未找到 g_tx_frame 声明"
src = src.replace(old_decl, hil_decl, 1)

old_link = """static bool link_exchange(c08b_link_tx_t *tx, c08b_link_rx_t *rx_out, bool *got_valid_rx)
{
    *got_valid_rx = false;
    if (!GET(LINK_RDY)) return false;"""

new_link = """static bool link_exchange(c08b_link_tx_t *tx, c08b_link_rx_t *rx_out, bool *got_valid_rx)
{
    *got_valid_rx = false;
    if (!GET(LINK_RDY)) {
#ifdef C08B_SWD_HIL
        if (g_swd_hil.enable == 1u) {
            c08b_link_tx_seal(tx);
            g_tx_frame = *tx;
            /* 同步翻转 PA15(LINK_CS / 蓝板绿灯 D2) 体现真实帧率 */
            SET(LINK_CS, 0);
            delay_us(4);
            SET(LINK_CS, 1);
            uint32_t h = g_swd_hil.tx_head;
            uint32_t t = g_swd_hil.tx_tail;
            if ((h - t) >= C08B_HIL_SLOTS) {
                return false;
            }
            g_swd_hil.tx_ring[h % C08B_HIL_SLOTS] = *tx;
            __DMB();
            g_swd_hil.tx_head = h + 1u;
            uint32_t rwr = g_swd_hil.rx_seq_wr;
            if (rwr != g_swd_hil.rx_seq_ack) {
                c08b_link_rx_t cand = g_swd_hil.rx_slot;
                __DMB();
                g_swd_hil.rx_seq_ack = rwr;
                if (c08b_link_rx_ok(&cand)) {
                    *rx_out = cand;
                    g_last_rx = cand;
                    *got_valid_rx = true;
                }
            }
            return true;
        }
#endif
        return false;
    }"""

assert old_link in src, "未找到 link_exchange 入口"
src = src.replace(old_link, new_link, 1)

old_main_init = """int main(void)
{
    clock_and_gpio_init();"""
new_main_init = """int main(void)
{
    clock_and_gpio_init();
#ifdef C08B_SWD_HIL
    g_swd_hil.magic = 0x48494C31u;
#endif"""
assert old_main_init in src, "未找到 main 入口"
src = src.replace(old_main_init, new_main_init, 1)
main_c.write_text(src)

# 3. XIAO nRF52840 Sense 专属零冲突引脚与 UF2 Bootloader 链接脚本
pins_xiao = FW_DIR / "nrf/pins_xiao_hil.h"
pins_xiao.write_text("""/* Seeed XIAO nRF52840 Sense 联调引脚映射（避开板载 QSPI / IMU / PDM / 32.768kHz 晶振） */
#pragma once
#define BENCH_EN_PIN   30u /* P0.30 = LED_GREEN（安全占位输出低，绝不碰 XL1） */
#define VBUS_SENSE_PIN  3u /* P0.03 = D1（外部互锁模拟输入，默认内部下拉=0） */
#define VBAT_SENSE_PIN  4u /* P0.04 = D4 / AIN2 */
#define PWR_HOLD_PIN    5u /* P0.05 = D5（供电保持模拟输出高） */
#define LINK_RDY_PIN   43u /* P1.11 = D6  <-> 蓝板 B6 (PB6) */
#define LINK_CS_PIN    44u /* P1.12 = D7  <-> 蓝板 A15 (PA15 / SPI3_CS) */
#define LINK_SCK_PIN   45u /* P1.13 = D8  <-> 蓝板 B3 (PB3 / SPI3_SCK) */
#define LINK_MISO_PIN  46u /* P1.14 = D9  <-> 蓝板 B4 (PB4 / SPI3_MISO) */
#define LINK_MOSI_PIN  47u /* P1.15 = D10 <-> 蓝板 B5 (PB5 / SPI3_MOSI) */
#define CHRG_N_PIN     17u /* P0.17 = 板载 BQ25100 ~CHG */
#define BUTTON_N_PIN   29u /* P0.29 = D3（默认内部上拉=1） */
#define OE_N_PIN       28u /* P0.28 = D2（默认内部下拉=0 模拟缓冲使能；拉高模拟 OE_OFF） */
#define MCU_RST_N_PIN  18u /* P0.18 = RESET */
#define LED_PIN        26u /* P0.26 = 板载红灯 LED_RED（低电平点亮） */
#define UART_TX_PIN     2u /* P0.02 = D0（115200 调试串口 TX） */
""")

nrf_ld = (FW_DIR / "nrf/nrf52840_s140.ld").read_text()
nrf_xiao_ld = FW_DIR / "nrf/nrf52840_xiao_s140.ld"
nrf_xiao_ld.write_text(nrf_ld.replace("LENGTH = 0x000D9000", "LENGTH = 0x000C6000"))

nrf_c_path = FW_DIR / "nrf/main.c"
nrf_c = nrf_c_path.read_text()
nrf_c = nrf_c.replace('#include "pins.h"', '#ifdef C08B_XIAO_HIL\n#include "pins_xiao_hil.h"\n#else\n#include "pins.h"\n#endif')
nrf_c = nrf_c.replace(
    "    gpio_in(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Disabled);\n    gpio_in(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);\n    gpio_in(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Disabled);\n    gpio_in(OE_N_PIN, GPIO_PIN_CNF_PULL_Disabled);",
    """#ifdef C08B_XIAO_HIL
    gpio_in(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Pulldown);
    gpio_in(OE_N_PIN, GPIO_PIN_CNF_PULL_Pulldown);
#else
    gpio_in(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Disabled);
    gpio_in(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Disabled);
    gpio_in(OE_N_PIN, GPIO_PIN_CNF_PULL_Disabled);
#endif"""
)
nrf_c_path.write_text(nrf_c)

# 4. 编译 L432 (128K + C08B_SWD_HIL) 与 XIAO nRF52840 S140 固件
subprocess.run(["make", "-C", str(FW_DIR), "clean"], check=True)
subprocess.run(["make", "-C", str(FW_DIR), "EXTRA_CFLAGS=-DC08B_SWD_HIL=1", "all"], check=True)

pio_pkg = Path.home() / ".platformio/packages"
arm_cc = str(pio_pkg / "toolchain-gccarmnoneeabi/bin/arm-none-eabi-gcc")
objcopy = str(pio_pkg / "toolchain-gccarmnoneeabi/bin/arm-none-eabi-objcopy")
size_bin = str(pio_pkg / "toolchain-gccarmnoneeabi/bin/arm-none-eabi-size")
core = str(pio_pkg / "framework-cmsis/CMSIS/Core/Include")
nrf_root = pio_pkg / "framework-arduinoadafruitnrf52-seeed/cores/nRF5"
mdk = str(nrf_root / "nordic/nrfx/mdk")
s140 = str(nrf_root / "nordic/softdevice/s140_nrf52_7.3.0_API/include")
nrfld = str(nrf_root / "linker")

xiao_elf = FW_DIR / "build/nrf_xiao_s140.elf"
xiao_bin = FW_DIR / "build/nrf_xiao_s140.bin"
xiao_uf2 = FW_DIR / "build/c08b_xiao_nrf52840_s140.uf2"

cmd = [
    arm_cc, "-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16",
    "-O2", "-g3", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
    "-ffunction-sections", "-fdata-sections",
    "-I", str(FW_DIR / "common"), "-I", str(FW_DIR / "nrf"),
    "-I", core, "-I", mdk, "-I", s140, "-I", f"{s140}/nrf52",
    "-DC08B_USE_S140=1", "-DC08B_XIAO_HIL=1", "-DNRF52840_XXAA", "-DS140", "-DSOFTDEVICE_PRESENT",
    "-DCONFIG_GPIO_AS_PINRESET", "-D__STARTUP_CLEAR_BSS", "-D__START=main",
    str(FW_DIR / "nrf/main.c"), f"{mdk}/system_nrf52840.c", f"{nrfld}/gcc_startup_nrf52840.S",
    "--specs=nano.specs", "--specs=nosys.specs",
    "-Wl,--gc-sections", "-Wl,--no-warn-rwx-segments", "-Wl,--print-memory-usage",
    "-T", str(nrf_xiao_ld), f"-Wl,-Map={FW_DIR}/build/nrf_xiao_s140.map",
    "-o", str(xiao_elf),
]
subprocess.run(cmd, check=True)
subprocess.run([objcopy, "-O", "binary", str(xiao_elf), str(xiao_bin)], check=True)
subprocess.run([size_bin, str(xiao_elf)], check=True)

raw = xiao_bin.read_bytes()
num_blocks = (len(raw) + 255) // 256
uf2_blocks = []
for bno in range(num_blocks):
    chunk = raw[bno * 256 : (bno + 1) * 256].ljust(256, b"\x00")
    hdr = struct.pack(
        "<IIIIIIII",
        0x0A324655, 0x9E5D5157, 0x00002000,
        0x00027000 + bno * 256, 256, bno, num_blocks, 0xADA52840
    )
    blk = hdr + chunk + b"\x00" * (512 - 32 - 256 - 4) + struct.pack("<I", 0x0AB16F30)
    assert len(blk) == 512
    uf2_blocks.append(blk)
xiao_uf2.write_bytes(b"".join(uf2_blocks))
print(f"生成 XIAO UF2 镜像成功: {xiao_uf2} ({len(uf2_blocks)} 块, {xiao_uf2.stat().st_size} 字节)")
