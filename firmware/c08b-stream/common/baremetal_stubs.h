/* 裸机 newlib-nano 最小系统调用空桩（替代 nosys.specs，消除 GCC 12+/13+ 链接器 .gnu.warning 告警）。 */
#pragma once
#include <sys/stat.h>

int _close(int fd) { (void)fd; return -1; }
int _fstat(int fd, struct stat *st) { (void)fd; if (st) st->st_mode = S_IFCHR; return 0; }
int _isatty(int fd) { (void)fd; return 1; }
int _lseek(int fd, int ptr, int dir) { (void)fd; (void)ptr; (void)dir; return 0; }
int _read(int fd, char *ptr, int len) { (void)fd; (void)ptr; (void)len; return 0; }
int _write(int fd, const char *ptr, int len) { (void)fd; (void)ptr; return len; }
int _getpid(void) { return 1; }
int _kill(int pid, int sig) { (void)pid; (void)sig; return -1; }
