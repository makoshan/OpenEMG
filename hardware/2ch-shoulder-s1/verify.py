"""用 KiCad 读回 S1，核对左右线序、R10 保留网络及图板一致性。"""
import csv
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPPING = {
    "J3": ("E1", "E3", "E2"),
    "J4": ("E4", "E6", "E5"),
}


def netlist(schematic, target):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
                    "-o", target, schematic], check=True)
    # NC 网络名包含符号名；统一映射为 None，同时保留实际引脚编号。
    return {(node.get("ref"), node.get("pin")): None if name.startswith("unconnected-") else name
            for net in ET.parse(target).iter("net") for name in [net.attrib["name"]]
            for node in net.findall("node")}


def check_pins(original, derived):
    expected = dict(original)
    for ref, old_contacts in MAPPING.items():
        for pin, contact in enumerate(old_contacts, start=1):
            expected[ref, str(pin)] = expected.pop((contact, "1"))
        expected[ref, "MP"] = None
    if expected != derived:
        raise ValueError(f"针脚差异 {set(expected.items()) ^ set(derived.items())}")


def main():
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        with (HERE / "r10-pins.csv").open(newline="") as source:
            original = {(row["reference"], row["pin"]): row["net"] or None
                        for row in csv.DictReader(source)}
        derived = netlist(HERE / "shoulder-s1.kicad_sch", work / "s1.xml")
        check_pins(original, derived)
        # 引脚同网仍可能贴错阻值，单独核原理图中的输入保护和互锁。
        components = {c.attrib["ref"]: c.findtext("value")
                      for c in ET.parse(work / "s1.xml").iter("comp")}
        critical = {f"R{i}": "300k" for i in (*range(1, 9), 13)}
        critical.update({"R14": "620k", "R16": "620k", "R32": "0R", "R25": "10k",
                         "J3": "S3B-PH-SM4-TB", "J4": "S3B-PH-SM4-TB"})
        for ref, value in critical.items():
            if components.get(ref) != value:
                raise ValueError(f"{ref} 应为 {value}，读回 {components.get(ref)}")
        # 反例：装线时互换右肩正负，必须能识别此错误。
        swapped = dict(derived)
        swapped["J4", "1"], swapped["J4", "3"] = swapped["J4", "3"], swapped["J4", "1"]
        try:
            check_pins(original, swapped)
        except ValueError:
            pass
        else:
            raise RuntimeError("未拦截右肩反接")
        for domain, suffix, extra in [
            ("sch", "kicad_sch", []),
            ("pcb", "kicad_pcb", ["--schematic-parity", "--refill-zones"]),
        ]:
            report = work / (domain + ".json")
            subprocess.run(["kicad-cli", domain, "erc" if domain == "sch" else "drc",
                            "--severity-all", "--exit-code-violations", "--format", "json",
                            *extra, "-o", report, HERE / ("shoulder-s1." + suffix)], check=True)
            result = json.loads(report.read_text())
            if domain == "pcb" and any(result[k] for k in ("violations", "unconnected_items", "schematic_parity")):
                raise ValueError("图板检查失败")
        print(f"{len(derived)} 个针脚已核对；右肩反接反例已拦截。")


if __name__ == "__main__":
    main()
