"""把导出的 .epro2 当新文件重新导入临时工程，验文件本身：件数、线数、飞线、DRC，再注入一段异网短线做阳性对照。
用法：python3 reimport_check.py <空.eprj3> <文件.epro2> <输出.json> [gerber.zip]"""
import base64, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'c08-eprj3-20261102'))
from jlccli import close, js, open_ready

eprj3, f, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
gz = Path(sys.argv[4]) if len(sys.argv) > 4 else None
sid, info = open_ready(eprj3)
DRC = r'''const cnt={};const walk=x=>{if(Array.isArray(x))x.forEach(walk);else if(x&&typeof x=="object"){if(x.errorType&&x.errorObjType){const k=x.errorType+"|"+x.errorObjType;cnt[k]=(cnt[k]||0)+1;}else Object.values(x).forEach(walk);}};walk(await eda.pcb_Drc.check(true,false,true));'''
try:
    for _ in range(60):
        before = js(sid, 'return await eda.dmt_Pcb.getAllPcbsInfo();')
        if before:
            break
        time.sleep(1)
    old = {p['uuid'] for p in before}
    b64 = base64.b64encode(f.read_bytes()).decode()
    js(sid, 'globalThis.__z="";return 0;')
    for i in range(0, len(b64), 256 * 1024):
        js(sid, 'globalThis.__z+="' + b64[i:i + 256 * 1024] + '";return 0;', 60000)
    r = js(sid, 'const bin=Uint8Array.from(atob(globalThis.__z),c=>c.charCodeAt(0));globalThis.__z="";'
                'return await eda.sys_FileManager.importProjectByProjectFile(new File([bin],"f04.epro2"),"JLCEDA Pro",'
                '{importOption:"ImportDocument"},{operation:"Existing Project",existingProjectUuid:' + json.dumps(info['uuid']) + '});', 300000)
    print('导入返回', str(r)[:160])
    for _ in range(30):
        pcbs = js(sid, 'return await eda.dmt_Pcb.getAllPcbsInfo();')
        new = [p for p in pcbs if p['uuid'] not in old]
        if new:
            break
        time.sleep(2)
    assert len(new) == 1, json.dumps(pcbs, ensure_ascii=False)[:400]
    res = js(sid, 'await eda.dmt_EditorControl.openDocument(' + json.dumps(new[0]['uuid']) + ');await new Promise(s=>setTimeout(s,4000));' + DRC + r'''
const ls=await eda.pcb_PrimitiveLine.getAll();
const o={件:(await eda.pcb_PrimitiveComponent.getAll()).length,线:ls.length,飞线:(await eda.pcb_Document.getRatlines()||{}).total,DRC:cnt};
const L=ls.find(l=>l.getState_Net()!="E1P"&&Math.abs(l.getState_EndX()-l.getState_StartX())>20);
const n=await eda.pcb_PrimitiveLine.create("E1P",L.getState_Layer(),L.getState_StartX(),L.getState_StartY(),L.getState_EndX(),L.getState_EndY(),5.9,false);
await new Promise(s=>setTimeout(s,1500));
const cnt0=cnt;
const c2={};const w2=x=>{if(Array.isArray(x))x.forEach(w2);else if(x&&typeof x=="object"){if(x.errorType&&x.errorObjType){const k=x.errorType+"|"+x.errorObjType;c2[k]=(c2[k]||0)+1;}else Object.values(x).forEach(w2);}};w2(await eda.pcb_Drc.check(true,false,true));
o.注入短路后=c2;o.压在网=L.getState_Net();
await eda.pcb_PrimitiveLine.delete([n.getState_PrimitiveId()]);await new Promise(s=>setTimeout(s,1500));
const c3={};const w3=x=>{if(Array.isArray(x))x.forEach(w3);else if(x&&typeof x=="object"){if(x.errorType&&x.errorObjType){const k=x.errorType+"|"+x.errorObjType;c3[k]=(c3[k]||0)+1;}else Object.values(x).forEach(w3);}};w3(await eda.pcb_Drc.check(true,false,true));
o.删除后=c3;o.删除后线=(await eda.pcb_PrimitiveLine.getAll()).length;return o;''', 300000)
    print(json.dumps(res, ensure_ascii=False))
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    if gz:
        n = js(sid, r'''const f=await eda.pcb_ManufactureData.getGerberFile("f04");if(!f)throw new Error("gerber 空");
const u=new Uint8Array(await f.arrayBuffer());let s="";for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));globalThis.__g=btoa(s);return globalThis.__g.length;''', 300000)
        CH = 2 * 1024 * 1024
        gz.write_bytes(base64.b64decode(''.join(js(sid, f'return globalThis.__g.slice({i},{i + CH});', 120000) for i in range(0, n, CH))))
        print('gerber', gz, gz.stat().st_size)
finally:
    close(sid)
