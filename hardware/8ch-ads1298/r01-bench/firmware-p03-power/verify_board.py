"""编译前核实际板包D0–D10映射，与F05同一判据。"""
from pathlib import Path
import re

Import('env')
if env.subst('$BOARD') != 'xiaoblesense_adafruit':
    raise ValueError('P03只接受XIAO nRF52840 Sense板包')
variant = Path(env.PioPlatform().get_package_dir('framework-arduinoadafruitnrf52-seeed')) / 'variants/Seeed_XIAO_nRF52840_Sense/variant.cpp'
body = variant.read_text().split('g_ADigitalPinMap[]', 1)[1].split('{', 1)[1].split('}', 1)[0]
pins = [int(v) for v in re.findall(r'\b\d+\b', re.sub(r'//[^\n]*', '', body))]
if pins[:11] != [2, 3, 28, 29, 4, 5, 43, 44, 45, 46, 47]:
    raise ValueError('实际XIAO板包D0–D10映射与已核接口不一致')
