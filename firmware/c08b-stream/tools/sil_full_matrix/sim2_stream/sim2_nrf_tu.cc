#include <climits>
#include <cstdarg>
#include <cstdbool>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>

#include "../mock_inc/nrf.h"

extern "C" void fw_copy_l432_rtt(char out[2048]);
uint32_t __data_start__ = 0x20004000u;

#define SystemCoreClock nrf_SystemCoreClock
#define SysTick_Config  nrf_SysTick_Config
#define main            fw_nrf_c_main
#define SysTick_Handler fw_nrf_c_systick
#define _SEGGER_RTT     nrf_SEGGER_RTT
#define log_sink        nrf_log_sink
#define rtt_init        nrf_rtt_init
#define rtt_write       nrf_rtt_write
#define logf_           nrf_logf_
#define _close          nrf_stub_close
#define _fstat          nrf_stub_fstat
#define _isatty         nrf_stub_isatty
#define _lseek          nrf_stub_lseek
#define _read           nrf_stub_read
#define _write          nrf_stub_write
#define _getpid         nrf_stub_getpid
#define _kill           nrf_stub_kill
#define volatile
#define while(cond)     while ((sim_loop_poll(), (cond)))

#include FW_MAIN_C

#undef main
#undef SysTick_Handler
#undef volatile
#undef while

extern "C" {
void fw_nrf_main_entry(void) { (void)fw_nrf_c_main(); }
void fw_nrf_systick(void)    { fw_nrf_c_systick(); }
void fw_copy_rtt_logs(char l432_out[2048], char nrf_out[2048]) {
    fw_copy_l432_rtt(l432_out);
    std::memcpy(nrf_out, rtt_up_buf, 2047);
    nrf_out[2047] = '\0';
}
}
