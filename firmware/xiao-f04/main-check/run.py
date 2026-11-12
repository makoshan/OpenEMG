"""主机读取实际main/stream/codec/dsp，替换Arduino/SDK外壳；不操作设备。"""
from pathlib import Path
import subprocess,hashlib,sys,json
root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parent.parent)
folder=Path(__file__).resolve().parent
start=hashlib.sha256((root/'src/main.cpp').read_bytes()).hexdigest()
(folder/"harness.cpp").write_text('\n#include <vector>\n#include "Arduino.h"\n#include "bluefruit.h"\nuint64_t fake_now=1000000;\nint suspend_depth=0;\nvoid(*resume_hook)()=nullptr;\nunsigned output_lows=0;\nbool fake_subscribed=true,resource_next=false;\nstd::vector<std::vector<uint8_t>>attempts,queued;\nFakeBluefruit Bluefruit;\nuint32_t sd_ble_gatts_hvx(uint16_t,const ble_gatts_hvx_params_t*p){assert(suspend_depth>0);std::vector<uint8_t>bytes(p->p_data,p->p_data+*p->p_len);attempts.push_back(bytes);if(resource_next){resource_next=false;return NRF_ERROR_RESOURCES;}queued.push_back(bytes);return NRF_SUCCESS;}\n#include "SOURCE_MAIN"\nstatic void emit(uint16_t id){ble_evt_t e{};e.header.evt_id=id;e.evt.common_evt.conn_handle=0;if(id==BLE_GAP_EVT_CONNECTED){assert(!Bluefruit.connection);Bluefruit.connection=new BLEConnection;}if(id==BLE_GAP_EVT_DISCONNECTED){delete Bluefruit.connection;Bluefruit.connection=nullptr;}assert(Bluefruit.callback);Bluefruit.callback(&e);}\nstatic void reconnect(){emit(BLE_GAP_EVT_DISCONNECTED);emit(BLE_GAP_EVT_CONNECTED);emit(BLE_GATTC_EVT_EXCHANGE_MTU_RSP);}\nstatic uint32_t seq(const std::vector<uint8_t>&p){return(uint32_t)p[4]|(uint32_t)p[5]<<8|(uint32_t)p[6]<<16|(uint32_t)p[7]<<24;}\nint main(){\n setup();assert(output_lows==((1u<<0)|(1u<<1)|(1u<<2)|(1u<<7)|(1u<<8)|(1u<<10)));\n emit(BLE_GAP_EVT_CONNECTED);emit(BLE_GATTC_EVT_EXCHANGE_MTU_RSP);\n resource_next=true;loop();assert(stream.count==1&&stream.pending_len==43&&stream.sent_packets==0);\n loop();assert(attempts.size()==2&&attempts[0]==attempts[1]&&stream.sent_samples==1&&seq(queued.back())==0&&(queued.back()[3]&2));\n // 停顿100ms：只生成32帧，其余帧数必须记为调度缺口。\n fake_now+=100000;loop();unsigned expected_skip=MAKO_V12_FS/10-32;\n assert(stream.scheduler_skipped==expected_skip&&stream.produced==33&&seq(queued.back())==expected_skip+1);assert(stream.latest_ready==0);\n // 刚取完快照就断连且复用同一句柄：旧代次这一轮不能发送。\n unsigned before=queued.size();resume_hook=reconnect;fake_now+=1000;loop();assert(queued.size()==before);\n loop();assert(queued.size()==before+1&&seq(queued.back())==0&&(queued.back()[3]&2));assert(stream.scheduler_skipped==0&&stream.sent_samples>=1);\n printf("fs=%u GPIO低电平顺序/资源重试字节/调度计数/重连复用均通过\\n",MAKO_V12_FS);delete Bluefruit.connection;\n}\n'.replace("SOURCE_MAIN",str(root/"src/main.cpp")))

objs=[]
for name in ('v12_stream','codec','dsp'):
    obj=folder/(name+'.o');objs.append(str(obj))
    subprocess.run(['clang','-std=c99','-O2','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-c',str(root/f'src/{name}.c'),'-o',str(obj)],check=True,capture_output=True,timeout=30)
for fs in (2000,4000):
    exe=folder/f'main-{fs}'
    command=['clang++','-std=c++17','-O2','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(folder),'-I',str(root/'src'),'-DMAKO_V12_AFE_ENABLED=0',f'-DMAKO_V12_FS={fs}',str(folder/'harness.cpp'),*objs,'-o',str(exe)]
    subprocess.run(command,check=True,capture_output=True,timeout=30)
    output=subprocess.run([str(exe)],check=True,capture_output=True,text=True,timeout=10)
    print(output.stdout.strip())
assert start==hashlib.sha256((root/'src/main.cpp').read_bytes()).hexdigest()
print('main_sha256',start)

# 直接编译真实main的禁用路径，确认错误配置确实被拒绝。
negative=[]
for name,old,new,message in [
    ('afe1','-DMAKO_V12_AFE_ENABLED=0','-DMAKO_V12_AFE_ENABLED=1','F04不得启用真实AFE'),
    ('fs1000','-DMAKO_V12_FS=4000','-DMAKO_V12_FS=1000','采样率候选只允许2000或4000')]:
    bad_command=[new if value==old else value for value in command]
    rejected=subprocess.run(bad_command,capture_output=True,text=True,timeout=30)
    assert rejected.returncode!=0 and message in rejected.stderr
    (folder/(name+'.log')).write_text(rejected.stderr)
    negative.append(dict(name=name,exit_code=rejected.returncode,expected_error=message))
(folder/'negative-compiles.json').write_text(json.dumps(negative,ensure_ascii=False,indent=2)+'\n')
print('AFE开启与非法采样率的编译反例均被拒绝')
