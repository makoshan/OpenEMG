# C08B 主控上电自检固件：make 生成 build/l432.{elf,hex,bin}、build/nrf.{elf,hex,bin}，并跑主机端测试。
# 依赖：PlatformIO 自带的 xPack arm-none-eabi-gcc 12.3.1（带 newlib-nano，可用 TC= 覆盖）；CMSIS 头文件来自 PlatformIO 包（路径可用 PIO_PKG 覆盖）：
#   framework-cmsis（Cortex-M 内核头）、framework-cmsis-stm32l4@1.7.4（L432 器件头和启动文件）、
#   framework-arduinoadafruitnrf52-seeed（其中 nordic/nrfx/mdk：nRF52840 器件头、启动文件、system 文件）。
PIO_PKG ?= $(HOME)/.platformio/packages
CORE    := $(PIO_PKG)/framework-cmsis/CMSIS/Core/Include
L4      := $(PIO_PKG)/framework-cmsis-stm32l4
MDK     := $(PIO_PKG)/framework-arduinoadafruitnrf52-seeed/cores/nRF5/nordic/nrfx/mdk
NRFLD   := $(PIO_PKG)/framework-arduinoadafruitnrf52-seeed/cores/nRF5/linker

TC      ?= $(PIO_PKG)/toolchain-gccarmnoneeabi/bin/
CC      := $(TC)arm-none-eabi-gcc
OBJCOPY := $(TC)arm-none-eabi-objcopy
SIZE    := $(TC)arm-none-eabi-size
ARCH    := -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
CFLAGS  := $(ARCH) -O2 -g3 -std=gnu11 -Wall -Wextra -Werror -Wno-unused-parameter -ffunction-sections -fdata-sections -I common
LDFLAGS := $(ARCH) --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections -Wl,--print-memory-usage

all: build/l432.hex build/nrf.hex host

build:
	mkdir -p build

l432/pins.h nrf/pins.h: tools/pins.py
	python3 tools/pins.py $(BOARD_JSON)

build/l432.elf: l432/main.c l432/l432.ld l432/pins.h common/report.h common/rtt.h | build
	$(CC) $(CFLAGS) -DSTM32L432xx -I l432 -I $(CORE) -I $(L4)/Include \
	  l432/main.c $(L4)/Source/Templates/system_stm32l4xx.c $(L4)/Source/Templates/gcc/startup_stm32l432xx.s \
	  $(LDFLAGS) -T l432/l432.ld -Wl,-Map=build/l432.map -o $@ -lm

build/nrf.elf: nrf/main.c nrf/nrf52840.ld nrf/pins.h common/report.h common/rtt.h | build
	$(CC) $(CFLAGS) -DNRF52840_XXAA -DCONFIG_GPIO_AS_PINRESET -D__STARTUP_CLEAR_BSS -D__START=main \
	  -I nrf -I $(CORE) -I $(MDK) \
	  nrf/main.c $(MDK)/system_nrf52840.c $(NRFLD)/gcc_startup_nrf52840.S \
	  $(LDFLAGS) -T nrf/nrf52840.ld -Wl,-Map=build/nrf.map -o $@

build/%.hex: build/%.elf
	$(OBJCOPY) -O ihex $< $@
	$(OBJCOPY) -O binary $< build/$*.bin
	$(SIZE) $<

# 主机端测试：报告结构布局、CRC、广播包构造（用本机 cc 编译运行）
host: build
	cc -std=c11 -Wall -Wextra -Werror -I common host_test/test_host.c -o build/test_host
	./build/test_host

clean:
	rm -rf build

.PHONY: all host clean
