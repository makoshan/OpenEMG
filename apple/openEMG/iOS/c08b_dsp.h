#ifndef C08B_DSP_H
#define C08B_DSP_H
#include "v12_dsp.h"

#define C08B_DSP_MAX_CHANNELS 16u

/* 在不改动冻结文件 v12_dsp.{h,c} 的前提下，把同一套整数二阶差分高通 + DF2T 二阶节
   扩展到 C08B 共用双核主控的 2 / 8 / 16 通道与 500 / 1000 / 2000 / 4000 Hz 采样率。 */
typedef struct {
 v12_dsp bank[2];
 unsigned channels;
 int initialized;
} c08b_dsp;

int c08b_dsp_init(c08b_dsp *s, unsigned sample_rate, unsigned channels, int notch);
void c08b_dsp_reset(c08b_dsp *s);
int c08b_dsp_frame(c08b_dsp *s, const int32_t *raw, unsigned raw_count, float *out, int *ready);
#endif
