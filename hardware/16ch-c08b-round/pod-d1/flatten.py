# 递归展开 Bambu 官方预设的 inherits / include（先父后子覆盖），输出单个 JSON 给 CLI
import json, sys
from pathlib import Path
P = Path("/Applications/BambuStudio.app/Contents/Resources/profiles/BBL")
def find(kind, name):
    for d in [P / kind]:
        f = d / f"{name}.json"
        if f.exists(): return f
    raise FileNotFoundError(kind + "/" + name)
def load(kind, name):
    d = json.loads(find(kind, name).read_text())
    out = {}
    if "inherits" in d: out.update(load(kind, d["inherits"]))
    for inc in d.get("include", []) or []:
        out.update(load(kind, inc))
    out.update({k: v for k, v in d.items() if k not in ("inherits", "include")})
    return out
kind, name, dst = sys.argv[1], sys.argv[2], sys.argv[3]
d = load(kind, name)
for kv in sys.argv[4:]:
    k, v = kv.split("=", 1); d[k] = json.loads(v)
d.setdefault("name", name)
if kind == "process": d["print_settings_id"] = name
if kind == "filament": d["filament_settings_id"] = [name]
Path(dst).write_text(json.dumps(d, indent=1))
print(dst, len(d), {k: d.get(k) for k in ("layer_height", "initial_layer_print_height", "printer_model", "nozzle_diameter", "filament_type", "enable_support", "detect_thin_wall", "wall_loops", "line_width", "outer_wall_line_width") if k in d})
