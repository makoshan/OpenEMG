/* nRF52840 裸机（不带 SoftDevice/bootloader）：flash 1 MB 从 0 开始，RAM 256 KB。
   符号名对齐 Nordic MDK 的 gcc_startup_nrf52840.S（__etext/__data_start__/__bss_start__/__bss_end__/__StackTop/__StackLimit/__StackSize）。 */
ENTRY(Reset_Handler)
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 0x100000
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 0x40000
}
SECTIONS
{
  .text :
  {
    KEEP(*(.isr_vector))
    *(.text*)
    KEEP(*(.init)) KEEP(*(.fini))
    *(.rodata*)
    KEEP(*(.eh_frame*))
  } > FLASH
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > FLASH
  __exidx_start = .;
  .ARM.exidx : { *(.ARM.exidx* .gnu.linkonce.armexidx.*) } > FLASH
  __exidx_end = .;
  __etext = .;
  .data : AT (__etext)
  {
    __data_start__ = .;
    *(.data*)
    . = ALIGN(4);
    PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array)) PROVIDE_HIDDEN(__preinit_array_end = .);
    . = ALIGN(4);
    PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array)) PROVIDE_HIDDEN(__init_array_end = .);
    . = ALIGN(4);
    PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array)) PROVIDE_HIDDEN(__fini_array_end = .);
    . = ALIGN(4);
    __data_end__ = .;
  } > RAM
  .bss (NOLOAD) :
  {
    . = ALIGN(4);
    __bss_start__ = .;
    *(.bss*) *(COMMON)
    . = ALIGN(4);
    __bss_end__ = .;
    PROVIDE(end = .); PROVIDE(__end__ = .);
  } > RAM
  /* 这份 Adafruit 启动文件把栈、堆段注释掉了，栈由这里定义：RAM 顶端 8 KB（启动时会填 0xADADADAD 方便看栈深） */
  __StackSize = 8192;
  __StackTop = ORIGIN(RAM) + LENGTH(RAM);
  __StackLimit = __StackTop - __StackSize;
  __HeapBase = __bss_end__;
  __HeapLimit = __StackLimit;
  ASSERT(__bss_end__ <= __StackLimit, "bss 压到栈了")
}
