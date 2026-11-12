/* nRF52840 + Nordic SoftDevice S140 v7.3.0 链接脚本：
 * S140 v7.3.0 占用 Flash 0x00000000..0x00026FFF，应用从 0x00027000 起；
 * RAM 从 0x20006000 起（为 1 条连接 + MTU 247 + DLE + HVN 队列预留 24 KB SoftDevice RAM）。
 */
ENTRY(Reset_Handler)
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x00027000, LENGTH = 0x000D9000
  RAM   (rwx) : ORIGIN = 0x20006000, LENGTH = 0x0003A000
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
    PROVIDE(__start_svc_data = .); KEEP(*(.svc_data)) PROVIDE(__stop_svc_data = .);
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
