#include "c08b_dsp.h"

/* 由 scipy.signal (butter HP15 + butter LP + iirnotch 50Hz Q30) 按 v12/dsp-f03/generate.py
   完全相同公式生成的 float32 十六进制字面量：
   - 500 Hz:  HP 15 Hz + LP 200 Hz（奈奎斯特 250 Hz）+ 可选 50 Hz Q30 陷波
   - 1000 Hz: HP 15 Hz + LP 400 Hz（奈奎斯特 500 Hz）+ 可选 50 Hz Q30 陷波
   - 2000 / 4000 Hz: 直接委托冻结版 v12_dsp_init（HP 15 Hz + LP 600 Hz + 可选 50 Hz Q30 陷波） */
static const float c08b_sos_500_0[3][6] = {
 {0x1.c018000000000p-1f, -0x1.c018000000000p+0f, 0x1.c018000000000p-1f, 0x1.0000000000000p+0f, -0x1.bc16fc0000000p+0f, 0x1.8832040000000p-1f},
 {0x1.bb3c260000000p-2f, 0x1.bb3c260000000p-1f, 0x1.bb3c260000000p-2f, 0x1.0000000000000p+0f, 0x1.0c71060000000p+0f, 0x1.2f3f6a0000000p-2f},
 {0x1.0000000000000p+0f, 0x1.0000000000000p+1f, 0x1.0000000000000p+0f, 0x1.0000000000000p+0f, 0x1.5227620000000p+0f, 0x1.43f6560000000p-1f}
};
static const float c08b_sos_500_1[4][6] = {
 {0x1.c018000000000p-1f, -0x1.c018000000000p+0f, 0x1.c018000000000p-1f, 0x1.0000000000000p+0f, -0x1.bc16fc0000000p+0f, 0x1.8832040000000p-1f},
 {0x1.bb3c260000000p-2f, 0x1.bb3c260000000p-1f, 0x1.bb3c260000000p-2f, 0x1.0000000000000p+0f, 0x1.0c71060000000p+0f, 0x1.2f3f6a0000000p-2f},
 {0x1.0000000000000p+0f, 0x1.0000000000000p+1f, 0x1.0000000000000p+0f, 0x1.0000000000000p+0f, 0x1.5227620000000p+0f, 0x1.43f6560000000p-1f},
 {0x1.fab1980000000p-1f, -0x1.99ec800000000p+0f, 0x1.fab1980000000p-1f, 0x1.0000000000000p+0f, -0x1.99ec800000000p+0f, 0x1.f563300000000p-1f}
};
static const float c08b_sos_1000_0[3][6] = {
 {0x1.defd5c0000000p-1f, -0x1.defd5c0000000p+0f, 0x1.defd5c0000000p-1f, 0x1.0000000000000p+0f, -0x1.ddeca80000000p+0f, 0x1.c01c200000000p-1f},
 {0x1.bb3c260000000p-2f, 0x1.bb3c260000000p-1f, 0x1.bb3c260000000p-2f, 0x1.0000000000000p+0f, 0x1.0c71060000000p+0f, 0x1.2f3f6a0000000p-2f},
 {0x1.0000000000000p+0f, 0x1.0000000000000p+1f, 0x1.0000000000000p+0f, 0x1.0000000000000p+0f, 0x1.5227620000000p+0f, 0x1.43f6560000000p-1f}
};
static const float c08b_sos_1000_1[4][6] = {
 {0x1.defd5c0000000p-1f, -0x1.defd5c0000000p+0f, 0x1.defd5c0000000p-1f, 0x1.0000000000000p+0f, -0x1.ddeca80000000p+0f, 0x1.c01c200000000p-1f},
 {0x1.bb3c260000000p-2f, 0x1.bb3c260000000p-1f, 0x1.bb3c260000000p-2f, 0x1.0000000000000p+0f, 0x1.0c71060000000p+0f, 0x1.2f3f6a0000000p-2f},
 {0x1.0000000000000p+0f, 0x1.0000000000000p+1f, 0x1.0000000000000p+0f, 0x1.0000000000000p+0f, 0x1.5227620000000p+0f, 0x1.43f6560000000p-1f},
 {0x1.fd55460000000p-1f, -0x1.e467920000000p+0f, 0x1.fd55460000000p-1f, 0x1.0000000000000p+0f, -0x1.e467920000000p+0f, 0x1.faaa8e0000000p-1f}
};

static int configure_bank(v12_dsp *b, unsigned fs, int notch) {
 if (fs == 2000u || fs == 4000u) return v12_dsp_init(b, fs, notch);
 b->initialized = 0;
 v12_dsp_reset(b);
 if (fs == 500u && notch == 0)  { b->coeff = c08b_sos_500_0;  b->sections = 3u; b->guard = 52u;   b->initialized = 1; return V12_DSP_OK; }
 if (fs == 500u && notch == 1)  { b->coeff = c08b_sos_500_1;  b->sections = 4u; b->guard = 660u;  b->initialized = 1; return V12_DSP_OK; }
 if (fs == 1000u && notch == 0) { b->coeff = c08b_sos_1000_0; b->sections = 3u; b->guard = 104u;  b->initialized = 1; return V12_DSP_OK; }
 if (fs == 1000u && notch == 1) { b->coeff = c08b_sos_1000_1; b->sections = 4u; b->guard = 1320u; b->initialized = 1; return V12_DSP_OK; }
 return V12_DSP_ARGUMENT;
}

void c08b_dsp_reset(c08b_dsp *s) {
 if (!s) return;
 v12_dsp_reset(&s->bank[0]);
 v12_dsp_reset(&s->bank[1]);
}

int c08b_dsp_init(c08b_dsp *s, unsigned sample_rate, unsigned channels, int notch) {
 if (!s) return V12_DSP_ARGUMENT;
 s->initialized = 0;
 if (channels != 2u && channels != 8u && channels != 16u) return V12_DSP_ARGUMENT;
 if (configure_bank(&s->bank[0], sample_rate, notch) != V12_DSP_OK) return V12_DSP_ARGUMENT;
 if (configure_bank(&s->bank[1], sample_rate, notch) != V12_DSP_OK) return V12_DSP_ARGUMENT;
 s->channels = channels;
 s->initialized = 1;
 return V12_DSP_OK;
}

int c08b_dsp_frame(c08b_dsp *s, const int32_t *raw, unsigned raw_count, float *out, int *ready) {
 unsigned i;
 int32_t in0[8];
 float out0[8];
 int r0 = 0, r1 = 0, rc;
 if (!s || !s->initialized || !raw || !out || !ready) return V12_DSP_ARGUMENT;
 if (s->channels == 16u) {
  if (raw_count != 16u) return V12_DSP_ARGUMENT;
 } else {
  if (raw_count != 8u && raw_count != s->channels) return V12_DSP_ARGUMENT;
 }
 /* 先校验全帧所有通道的 24 位有符号码值范围，防止 16 路第 2 组越界时第 1 组已推进状态。 */
 for (i = 0; i < raw_count; ++i)
  if (raw[i] < -8388608 || raw[i] > 8388607) return V12_DSP_CODE_RANGE;
 for (i = 0; i < 8u; ++i)
  in0[i] = (i < raw_count) ? raw[i] : 0;
 rc = v12_dsp_frame(&s->bank[0], in0, out0, &r0);
 if (rc != V12_DSP_OK) return rc;
 for (i = 0; i < (s->channels < 8u ? s->channels : 8u); ++i)
  out[i] = out0[i];
 if (s->channels == 16u) {
  rc = v12_dsp_frame(&s->bank[1], raw + 8u, out + 8u, &r1);
  if (rc != V12_DSP_OK) return rc;
  *ready = (r0 && r1) ? 1 : 0;
 } else {
  *ready = r0;
 }
 return V12_DSP_OK;
}
