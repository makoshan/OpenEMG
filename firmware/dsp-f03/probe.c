#include "v12_dsp.h"
#include <stdio.h>
#include <stdlib.h>
/* 仅主机合成检查入口，目标 MCU 不编译此文件。 */
int main(int argc, char **argv) {
 v12_dsp state;
 char line[512];
 int32_t raw[8];
 float out[8];
 int ready, i, rc;
 if (argc!=3 || v12_dsp_init(&state, (unsigned)atoi(argv[1]), atoi(argv[2]))) return 2;
 while (fgets(line, sizeof(line), stdin)) {
  if (line[0]=='R') { v12_dsp_reset(&state); continue; }
  if (sscanf(line, "%d %d %d %d %d %d %d %d", &raw[0], &raw[1], &raw[2], &raw[3], &raw[4], &raw[5], &raw[6], &raw[7])!=8) return 3;
  rc=v12_dsp_frame(&state, raw, out, &ready);
  printf("%d", rc);
  if (!rc) {
   printf(",%d", ready);
   for (i=0; i<8; ++i) printf(",%.9g", (double)out[i]);
  }
  putchar('\n');
 }
 return 0;
}
