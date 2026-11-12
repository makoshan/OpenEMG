/* nRF52840 免 SoftDevice 裸机诊断链接脚本：flash 从 0x00000000 开始，供首板未刷 S140 时验证双核 SPI 流与广播。 */
ENTRY(Reset_Handler)
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00100000
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 0x00040000
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
  __StackSize = 8192;
  __StackTop = ORIGIN(RAM) + LENGTH(RAM);
  __StackLimit = __StackTop - __StackSize;
  __HeapBase = __bss_end__;
  __HeapLimit = __StackLimit;
  ASSERT(__bss_end__ <= __StackLimit, "bss 压到栈了")
}
