"""F04 八通道软板：KiCad 工程（原理图 + K9 板）压成 zip，导入已建好的空 .eprj3，再配成一块板。
用法：python3 import_f04.py <工程.eprj3> <kicad.zip>
走官方 CLI 无头会话，不碰用户开着的窗口；要在 Bash 沙箱外跑（沙箱里 open 不返回）。"""
import base64, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'c08-eprj3-20261102'))
from jlccli import close, js, open_ready

eprj3, z = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sid, info = open_ready(eprj3)
print('会话', sid, info['friendlyName'], info['uuid'])
DOCS = ('return {pcbs: await eda.dmt_Pcb.getAllPcbsInfo(), schs: await eda.dmt_Schematic.getAllSchematicsInfo(),'
        'boards: await eda.dmt_Board.getAllBoardsInfo()};')
try:
    for _ in range(60):
        before = js(sid, DOCS)
        if before['pcbs'] and before['schs']:
            break
        time.sleep(2)
    assert before['pcbs'] and before['schs'], '文档列表一直为空'
    print('导入前', json.dumps(before, ensure_ascii=False)[:500])

    b64 = base64.b64encode(z.read_bytes()).decode()
    js(sid, 'globalThis.__z="";return 0;')
    for i in range(0, len(b64), 256 * 1024):
        js(sid, 'globalThis.__z+="' + b64[i:i + 256 * 1024] + '";return 0;', 60000)
    assert js(sid, 'return globalThis.__z.length;') == len(b64)
    r = js(sid, 'const bin=Uint8Array.from(atob(globalThis.__z),c=>c.charCodeAt(0));globalThis.__z="";'
                'return await eda.sys_FileManager.importProjectByProjectFile(new File([bin],' + json.dumps(z.name) + '),"KiCad",'
                '{importOption:"ImportDocument"},{operation:"Existing Project",existingProjectUuid:' + json.dumps(info['uuid']) + '});',
           300000)
    print('导入返回', json.dumps(r, ensure_ascii=False)[:300])

    oldp = {p['uuid'] for p in before['pcbs']}
    olds = {s['uuid'] for s in before['schs']}
    for _ in range(30):
        now = js(sid, DOCS)
        newp = [p for p in now['pcbs'] if p['uuid'] not in oldp]
        news = [s for s in now['schs'] if s['uuid'] not in olds]
        if newp and news:
            break
        time.sleep(3)
    print('导入后', json.dumps(now, ensure_ascii=False)[:900])
    assert len(newp) == 1 and len(news) == 1, '新文档数不对：PCB %d 原理图 %d' % (len(newp), len(news))

    # 删 init 自带的空板、空 PCB、空原理图，把导入的原理图和 PCB 配成一块板
    for b in before['boards']:
        js(sid, 'return await eda.dmt_Board.deleteBoard(' + json.dumps(b['name']) + ');')
    for u in oldp:
        js(sid, 'return await eda.dmt_Pcb.deletePcb(' + json.dumps(u) + ');')
    for u in olds:
        js(sid, 'return await eda.dmt_Schematic.deleteSchematic(' + json.dumps(u) + ');')
    print('配板', js(sid, 'return await eda.dmt_Board.createBoard(' + json.dumps(news[0]['uuid']) + ',' + json.dumps(newp[0]['uuid']) + ');'))
    print('结果', json.dumps(js(sid, DOCS), ensure_ascii=False)[:900])
    js(sid, 'await eda.dmt_EditorControl.openDocument(' + json.dumps(newp[0]['uuid']) + ');await new Promise(s=>setTimeout(s,3000));'
            'return await eda.pcb_Document.save();')
finally:
    close(sid)
