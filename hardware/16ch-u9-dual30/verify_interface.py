"""直接从两份嘉立创工程读取板间焊盘。运行 python3 verify_interface.py。"""
import csv
import json
import zipfile
from pathlib import Path
P = Path(__file__).resolve().parent

def afe_pads():
    with zipfile.ZipFile(P / 'AFE-30P.epro') as z:
        pcb = next(name for name in z.namelist() if name.endswith('.epcb'))
        rows = [json.loads(line) for line in z.read(pcb).splitlines() if line]
    rows = rows[max(i for i,r in enumerate(rows) if r[:2] == ['DOCTYPE','PCB']):]
    refs = {r[3]:r[8] for r in rows if r[0]=='ATTR' and r[7]=='Designator'}
    return {(refs[r[1]],int(r[2])):r[3] for r in rows
            if r[0]=='PAD_NET' and r[1] in refs and r[2].isdigit()}

def main_pads():
    with zipfile.ZipFile(P / 'MCU-U9.epro2') as z:
        doc = z.read(next(n for n in z.namelist() if n.endswith('.epru')))
    active = False
    pads, connectors = {}, set()
    for line in doc.decode().splitlines():
        if '||' not in line:
            continue
        left, right = line.split('||',1)
        right = right.removesuffix('|')
        if not right:
            continue
        h = json.loads(left)
        if h['type'] not in ('DOCHEAD','ATTR','PAD_NET'):
            continue
        v, _ = json.JSONDecoder().raw_decode(right)
        if h['type']=='DOCHEAD':
            active = v['docType']=='PCB'
        elif active and h['type']=='ATTR' and v.get('key')=='Designator' and v.get('value')=='FPC1':
            connectors.add(v['parentId'])
        elif active and h['type']=='PAD_NET':
            _, ref, pin, _ = json.loads(h['id'])
            if pin.isdigit():
                pads[ref,int(pin)] = v['padNet']
    assert len(connectors)==1
    ref = connectors.pop()
    return [pads[ref,i] for i in range(1,21)]

main = main_pads()
afe = afe_pads()
expected_main = ['GND','','AFE_DRDY_B','AFE_CS_B','AFE_DIN','AFE_PWDN','AFE_RESET','','AFE_START','AFE_CS_A','AFE_SCLK','GND','','GND','DOUT_B','AFE_GPIO3','ADS_DRDY_A','','3V3_AFE','3V3_AFE']
expected_afe = ['GND','GND','DRDY2#','CS#2','DIN','PWDN#','RESET#','CLK','START','CS#','SCLK','GND','GND','GND','DOUT','GPIO3','DRDY#','CLKSEL','+3.3V','+3.3V']
for i, (host, target) in enumerate(zip(expected_main,expected_afe),1):
    assert (main[i-1],afe['FPC2',21-i])==(host,target), f'主控第 {i} 脚不匹配'
assert afe['U2',39]==afe['FPC2',17] and afe['U2',47]==afe['FPC2',18]
with (P/'20针接口.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['主控FPC1','主控网络','采集FPC2','采集网络'])
    for i,net in enumerate(main,1):w.writerow([i,net,21-i,afe['FPC2',21-i]])
print('20/20 脚与预期配对一致，U2 的 39 和 47 脚已核。')
