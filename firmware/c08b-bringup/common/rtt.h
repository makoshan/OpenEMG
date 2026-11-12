/* 最小 SEGGER RTT 上行通道：调试器（pyocd rtt、J-Link RTT Viewer、openocd rtt）扫内存里的 "SEGGER RTT" 控制块读日志。
   只写不读、满了就丢，不会卡住程序。每个固件只在一个 .c 里 #define RTT_IMPL 后包含。 */
#pragma once
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *name;
    char *buf;
    unsigned size;
    volatile unsigned wr;
    volatile unsigned rd;
    unsigned flags;
} rtt_buf_t;

typedef struct {
    char id[16];
    int max_up, max_down;
    rtt_buf_t up[1], down[1];
} rtt_cb_t;

void rtt_init(void);
void rtt_write(const char *s, unsigned n);
void logf_(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

#ifdef RTT_IMPL
static char rtt_up_buf[2048];
static char rtt_down_buf[16];
rtt_cb_t _SEGGER_RTT __attribute__((aligned(4)));

void rtt_init(void)
{
    rtt_cb_t *c = &_SEGGER_RTT;
    memset(c, 0, sizeof *c);
    c->max_up = 1; c->max_down = 1;
    c->up[0] = (rtt_buf_t){"Terminal", rtt_up_buf, sizeof rtt_up_buf, 0, 0, 0};
    c->down[0] = (rtt_buf_t){"Terminal", rtt_down_buf, sizeof rtt_down_buf, 0, 0, 0};
    /* 标识最后写，且倒着写，免得调试器在初始化一半时认到它（SEGGER 原版同样做法） */
    static const char tag[] = "SEGGER RTT";
    for (int i = (int)sizeof tag - 2; i >= 0; i--) c->id[i] = tag[i];
}

void rtt_write(const char *s, unsigned n)
{
    rtt_buf_t *b = &_SEGGER_RTT.up[0];
    for (unsigned i = 0; i < n; i++) {
        unsigned nx = (b->wr + 1) % b->size;
        if (nx == b->rd) return;   /* 满了丢掉 */
        b->buf[b->wr] = s[i];
        b->wr = nx;
    }
}

void logf_(const char *fmt, ...)
{
    char line[160];
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof line - 1) n = sizeof line - 1;
    rtt_write(line, (unsigned)n);
    extern void log_sink(const char *s, unsigned n);  /* 各固件自己再输出一份（nRF 走 UART，L432 空实现） */
    log_sink(line, (unsigned)n);
}
#endif
