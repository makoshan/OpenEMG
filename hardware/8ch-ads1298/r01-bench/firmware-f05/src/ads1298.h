#pragma once
#include <stdint.h>
#include <stddef.h>
namespace v12 {
// ExternalRld：外部输入 + 右腿驱动（8 对全进平均），4 号留给 STOP。
enum class Input : uint8_t { Test=1, Shorted=2, External=3, ExternalRld=5 };
enum class Fault : uint8_t { None, Locked, Argument, Rails, Identity, Readback, Frame, Overrun, Timeout, Cancelled };
struct BenchProof { bool measured; uint32_t por_wait_us; uint32_t reference_wait_us; };
struct AdsHal {
 virtual ~AdsHal()=default;
 virtual void power(bool)=0;
 virtual void pwdn(bool)=0;
 virtual void reset(bool)=0;
 virtual void clocksel(bool)=0;
 virtual void cs(bool)=0;
 virtual uint8_t transfer(uint8_t)=0;
 virtual void wait(uint32_t)=0;
 virtual bool rails_good()=0;
 virtual bool session_valid()=0;
 virtual void capture(bool)=0;
};
class Ads1298 {
 AdsHal &h;
 void command(uint8_t);
 uint8_t read_reg(uint8_t);
 bool write_checked(uint8_t,uint8_t);
 public:
 bool active=false;
 Fault fault=Fault::None;
 explicit Ads1298(AdsHal &hal):h(hal){}
 void stop(Fault why=Fault::None);
 bool start(unsigned,Input,const BenchProof&);
 bool read(uint8_t frame[27]);
 static bool decode(const uint8_t*,size_t,int32_t out[8],uint32_t *status);
};
}
