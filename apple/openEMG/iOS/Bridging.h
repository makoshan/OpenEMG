// 直接用 F05 固件与主机端同一份滤波（不复制源码）：v12/manufacturing-r01/firmware-f05/src/v12_dsp.{h,c}
// 并通过 c08b_dsp.{h,c} 扩展到 C08B 的 2 / 8 / 16 通道与 500 / 1000 / 2000 / 4000 Hz。
#include "v12_dsp.h"
#include "c08b_dsp.h"
