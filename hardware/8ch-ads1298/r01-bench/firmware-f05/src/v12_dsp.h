#ifndef V12_DSP_H
#define V12_DSP_H
#include <stddef.h>
#include <stdint.h>
#define V12_DSP_CHANNELS 8u
#define V12_DSP_SECTIONS 4u
typedef struct {
 const float (*coeff)[6];
 float state[V12_DSP_CHANNELS][V12_DSP_SECTIONS][2];
 int32_t previous_raw[V12_DSP_CHANNELS], previous_delta[V12_DSP_CHANNELS];
 unsigned sections, guard, processed;
 int initialized, anchored;
} v12_dsp;
enum { V12_DSP_OK=0, V12_DSP_ARGUMENT=-1, V12_DSP_CODE_RANGE=-2 };
/* 不操作设备；必须串行调用。输入/输出不得重叠。 */
int v12_dsp_init(v12_dsp *s, unsigned sample_rate, int notch);
void v12_dsp_reset(v12_dsp *s);
/* 每次一帧八路；输出单位为ADC正满量程比例，raw不改写。 */
int v12_dsp_frame(v12_dsp *s, const int32_t raw[8], float out[8], int *ready);
/* 主机回放桥接：内部状态只在明确 reset 时清除，无堆分配。 */
size_t v12_dsp_state_size(void);
int v12_dsp_block(v12_dsp *s, const int32_t *raw, size_t frames, float *out, uint8_t *ready);
#endif
