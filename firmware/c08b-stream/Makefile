# C08B 共用双核主控（R4U6 / R4U6N）2/8/16ch 实时流式采集候选固件构建规则
#
# 目标：
#   - make host     ：仅需标准 C11 编译器，不依赖本地 PlatformIO CMSIS 包（Ubuntu CI 可直跑）
#   - make all      ：在本机完整编译 $(BUILD_DIR)/l432.{elf,hex,bin}、$(BUILD_DIR)/nrf_s140.{elf,hex,bin}、$(BUILD_DIR)/nrf_nosd.{elf,hex,bin} 并跑 host 单测

PIO_PKG   ?= $(HOME)/.platformio/packages
PY        ?= python3
BUILD_DIR ?= build
CORE      := $(PIO_PKG)/framework-cmsis/CMSIS/Core/Include
L4        := $(PIO_PKG)/framework-cmsis-stm32l4
NRF_ROOT  := $(PIO_PKG)/framework-arduinoadafruitnrf52-seeed/cores/nRF5
MDK       := $(NRF_ROOT)/nordic/nrfx/mdk
S140      := $(NRF_ROOT)/nordic/softdevice/s140_nrf52_7.3.0_API/include
NRFLD     := $(NRF_ROOT)/linker

TC        ?= $(PIO_PKG)/toolchain-gccarmnoneeabi/bin/
ARM_CC    := $(TC)arm-none-eabi-gcc
OBJCOPY   := $(TC)arm-none-eabi-objcopy
SIZE      := $(TC)arm-none-eabi-size
HOST_CC   ?= cc

ARCH      := -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
EXTRA_CFLAGS ?=
CFLAGS    := $(ARCH) -O2 -g3 -std=gnu11 -Wall -Wextra -Werror -Wno-unused-parameter -ffunction-sections -fdata-sections -I common $(EXTRA_CFLAGS)
LDFLAGS   := $(ARCH) --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections -Wl,--no-warn-rwx-segments -Wl,--print-memory-usage

all: $(BUILD_DIR)/l432.hex $(BUILD_DIR)/nrf_s140.hex $(BUILD_DIR)/nrf_nosd.hex host

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

pins:
	$(PY) -B tools/pins.py $(BOARD_JSON)

$(BUILD_DIR)/l432.elf: l432/main.c l432/l432.ld l432/pins.h common/stream_proto.h common/bench_release.h common/rtt.h common/baremetal_stubs.h | $(BUILD_DIR)
	$(ARM_CC) $(CFLAGS) -DSTM32L432xx -I l432 -I $(CORE) -I $(L4)/Include \
	  l432/main.c $(L4)/Source/Templates/system_stm32l4xx.c $(L4)/Source/Templates/gcc/startup_stm32l432xx.s \
	  $(LDFLAGS) -T l432/l432.ld -Wl,-Map=$(BUILD_DIR)/l432.map -o $@

$(BUILD_DIR)/nrf_s140.elf: nrf/main.c nrf/nrf52840_s140.ld nrf/pins.h common/stream_proto.h common/bench_release.h common/rtt.h common/baremetal_stubs.h | $(BUILD_DIR)
	$(ARM_CC) $(CFLAGS) -DC08B_USE_S140=1 -DNRF52840_XXAA -DS140 -DSOFTDEVICE_PRESENT \
	  -DCONFIG_GPIO_AS_PINRESET -D__STARTUP_CLEAR_BSS -D__START=main \
	  -I nrf -I $(CORE) -I $(MDK) -I $(S140) -I $(S140)/nrf52 \
	  nrf/main.c $(MDK)/system_nrf52840.c $(NRFLD)/gcc_startup_nrf52840.S \
	  $(LDFLAGS) -T nrf/nrf52840_s140.ld -Wl,-Map=$(BUILD_DIR)/nrf_s140.map -o $@

$(BUILD_DIR)/nrf_nosd.elf: nrf/main.c nrf/nrf52840_nosd.ld nrf/pins.h common/stream_proto.h common/bench_release.h common/rtt.h common/baremetal_stubs.h | $(BUILD_DIR)
	$(ARM_CC) $(CFLAGS) -DC08B_USE_S140=0 -DNRF52840_XXAA \
	  -DCONFIG_GPIO_AS_PINRESET -D__STARTUP_CLEAR_BSS -D__START=main \
	  -I nrf -I $(CORE) -I $(MDK) \
	  nrf/main.c $(MDK)/system_nrf52840.c $(NRFLD)/gcc_startup_nrf52840.S \
	  $(LDFLAGS) -T nrf/nrf52840_nosd.ld -Wl,-Map=$(BUILD_DIR)/nrf_nosd.map -o $@

$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf
	$(OBJCOPY) -O ihex $< $@
	$(OBJCOPY) -O binary $< $(BUILD_DIR)/$*.bin
	$(SIZE) $<

host: $(BUILD_DIR)
	$(HOST_CC) -std=c11 -O2 -Wall -Wextra -Werror -I common host_test/test_stream_host.c -o $(BUILD_DIR)/test_stream_host
	$(BUILD_DIR)/test_stream_host

clean:
	/bin/rm -rf $(BUILD_DIR)

.PHONY: all pins host clean
