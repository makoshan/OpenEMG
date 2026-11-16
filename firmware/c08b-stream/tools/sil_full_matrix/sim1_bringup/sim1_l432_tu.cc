#include <climits>
#include <cstdarg>
#include <cstdbool>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>

#include "../mock_inc/stm32l432xx.h"

#define main            fw_l432_c_main
#define SysTick_Handler fw_l432_c_systick
#define _SEGGER_RTT     l432_SEGGER_RTT
#define log_sink        l432_log_sink
#define volatile
#define while(cond)     while ((sim_loop_poll(), (cond)))

#include FW_MAIN_C

#undef main
#undef SysTick_Handler
#undef volatile
#undef while

extern "C" {
void fw_l432_main_entry(void) { (void)fw_l432_c_main(); }
void fw_l432_systick(void)    { fw_l432_c_systick(); }
void fw_copy_l432_rtt(char out[2048]) {
    std::memcpy(out, rtt_up_buf, 2047);
    out[2047] = '\0';
}
}
