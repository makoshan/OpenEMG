#include "v12_dsp.h"
#include "coefficients.h"

void v12_dsp_reset(v12_dsp *s) {
 unsigned ch, stage;
 if (!s) return;
 for (ch=0; ch<V12_DSP_CHANNELS; ++ch)
  for (stage=0; stage<V12_DSP_SECTIONS; ++stage) {
   s->state[ch][stage][0]=0.0f;
   s->state[ch][stage][1]=0.0f;
  }
 s->processed=0;
 s->anchored=0;
}

int v12_dsp_init(v12_dsp *s, unsigned sample_rate, int notch) {
 if (!s) return V12_DSP_ARGUMENT;
 s->initialized=0;
 v12_dsp_reset(s);
 if (configure(s, sample_rate, notch)) return V12_DSP_ARGUMENT;
 s->initialized=1;
 return V12_DSP_OK;
}

int v12_dsp_frame(v12_dsp *s, const int32_t raw[8], float out[8], int *ready) {
 unsigned ch, stage;
 if (!s || !s->initialized || !raw || !out || !ready) return V12_DSP_ARGUMENT;
 /* 一帧先检查全部通道，拒绝时不部分推进滤波器。 */
 for (ch=0; ch<V12_DSP_CHANNELS; ++ch)
  if (raw[ch] < -8388608 || raw[ch] > 8388607) return V12_DSP_CODE_RANGE;
 for (ch=0; ch<V12_DSP_CHANNELS; ++ch) {
  /* 高通分子固定为b0*(1-z^-1)^2。在整数域先二阶差分，避免
     大直流/偏置跳变在float32中反复抵消；不扩大采样前PGA范围。
     首码视为此前恒定输入，等价于高通按首码稳态启动。 */
  const float *hp=s->coeff[0];
  float *history=s->state[ch][0];
  if (!s->anchored) {
   s->previous_raw[ch]=raw[ch];
   s->previous_delta[ch]=0;
  }
  int32_t delta=raw[ch]-s->previous_raw[ch];
  int32_t second=delta-s->previous_delta[ch];
  float x=hp[0]*((float)second/8388608.0f)-hp[4]*history[0]-hp[5]*history[1];
  history[1]=history[0]; history[0]=x;
  s->previous_raw[ch]=raw[ch]; s->previous_delta[ch]=delta;
  for (stage=1; stage<s->sections; ++stage) {
   const float *c=s->coeff[stage];
   float *z=s->state[ch][stage];
   float y=c[0]*x+z[0];
   z[0]=c[1]*x-c[4]*y+z[1];
   z[1]=c[2]*x-c[5]*y;
   x=y;
  }
  out[ch]=x;
 }
 s->anchored=1;
 *ready=(s->processed>=s->guard);
 if (s->processed<s->guard) ++s->processed;
 return V12_DSP_OK;
}

size_t v12_dsp_state_size(void) { return sizeof(v12_dsp); }

int v12_dsp_block(v12_dsp *s, const int32_t *raw, size_t frames, float *out, uint8_t *ready) {
 size_t i;
 int valid, rc;
 unsigned ch;
 if (!s || !s->initialized || !raw || !out || !ready || frames>SIZE_MAX/8u) return V12_DSP_ARGUMENT;
 /* 整块预检，避免错误块只处理了一半。 */
 for (i=0; i<frames; ++i)
  for (ch=0; ch<8u; ++ch)
   if (raw[i*8u+ch] < -8388608 || raw[i*8u+ch] > 8388607) return V12_DSP_CODE_RANGE;
 for (i=0; i<frames; ++i) {
  rc=v12_dsp_frame(s, raw+i*8u, out+i*8u, &valid);
  if (rc) return rc;
  ready[i]=(uint8_t)valid;
 }
 return V12_DSP_OK;
}
