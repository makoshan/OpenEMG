// 仅模拟外部寄存器与GPIO事件；不代表DMA速度或实物电平。
#include "src/imu_board.h"
#include <cassert>
#include <cstdio>
TwimRegs regs;unsigned power_value=0;
int main(){
 v12::ImuBoard h;uint8_t data[16];
 assert(h.power(true) && power_value==HIGH);
 assert(h.read(0x1e,16));
 regs.EVENTS_STOPPED=1;regs.TXD.AMOUNT=1;regs.RXD.AMOUNT=16;
 assert(h.poll(data,16)==1);
 // RXD.AMOUNT保留16，下一次纯写必须正常完成。
 assert(h.write(0x12,0x44));regs.EVENTS_STOPPED=1;regs.TXD.AMOUNT=2;
 assert(h.poll(data,0)==1);
 assert(h.read(0x1e,16));const unsigned tx=h.tx[0];
 assert(!h.power(false) && h.busy && h.stopping && regs.ENABLE && power_value==HIGH);
 assert(!h.write(0x12,1) && h.tx[0]==tx);
 regs.EVENTS_ERROR=1;assert(h.poll(data,16)==0 && regs.ENABLE);
 assert(regs.TASKS_STOP==1 && regs.TASKS_RESUME==1);
 assert(!h.power(false));regs.EVENTS_STOPPED=1;
 assert(h.power(false) && !h.busy && !h.owns && !regs.ENABLE && power_value==LOW);
 // 完整STOPPED后才允许新代次；transfer必须清除旧STOPPED，不能接受旧完成。
 assert(h.power(true) && h.read(0x0f,1) && !regs.EVENTS_STOPPED);
 assert(h.poll(data,1)==0);
 regs.EVENTS_STOPPED=1;regs.TXD.AMOUNT=1;regs.RXD.AMOUNT=1;
 assert(h.poll(data,1)==1 && h.power(false));
 puts("PASS: 真IMU HAL纯写旧RX计数、异步停止、ERROR与旧完成事件边界；未实物验收");
}
