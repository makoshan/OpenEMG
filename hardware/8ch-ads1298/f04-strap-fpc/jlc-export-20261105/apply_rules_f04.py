"""把 F04 的 .kicad_dru 规则写进嘉立创工程：铜间距 0.10、线宽 ≥ 0.15、铜到板边 0.30。默认 6 mil 间距会误报 88 条。
用法：python3 apply_rules_f04.py <工程.eprj3>"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'c08-eprj3-20261102'))
from jlccli import close, js, open_ready

sid, _ = open_ready(Path(sys.argv[1]).resolve())
try:
    print(json.dumps(js(sid, r'''
const sleep = ms => new Promise(r => setTimeout(r, ms));
for (let i = 0; i < 60 && !((await eda.dmt_Pcb.getAllPcbsInfo()) || []).length; i++) await sleep(1000);
const pcb = (await eda.dmt_Pcb.getAllPcbsInfo())[0];
await eda.dmt_EditorControl.openDocument(pcb.uuid); await sleep(3000);
const c = JSON.parse(JSON.stringify((await eda.pcb_Drc.getCurrentRuleConfiguration()).config));
const ss = c.Spacing['Safe Spacing'].copperThickness1oz, rows = ss.row, cols = ss.column;
ss.tables['1'].content.forEach((r, i) => r.forEach((_, j) => {
  if (/Text|Line|Slot|Hole|Zone/.test(rows[i] + cols[j])) {}
  else if (rows[i] == 'Board Outline' || cols[j] == 'Board Outline') r[j] = 0.3;
  else r[j] = 0.1; }));
c.Physics.Track.copperThickness1oz.form.data['1'].minValue = 0.15;
const ok = await eda.pcb_Drc.overwriteCurrentRuleConfiguration(c);
const rb = (await eda.pcb_Drc.getCurrentRuleConfiguration()).config;
const saved = await eda.pcb_Document.save();
return {ok, saved, rows, cols, table: rb.Spacing['Safe Spacing'].copperThickness1oz.tables['1'].content, track: rb.Physics.Track.copperThickness1oz.form.data['1'].minValue};''', 120000), ensure_ascii=False)[:1400])
finally:
    close(sid)
