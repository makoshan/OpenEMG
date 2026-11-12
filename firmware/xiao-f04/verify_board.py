"""编译前核实际板包，不能凭board名字默认引脚一致。"""
from pathlib import Path
import hashlib
import json
import re
from sdk_patch import patched_bluefruit


def check_variant(text):
    body=text.split('g_ADigitalPinMap[]', 1)[1].split('{', 1)[1].split('}', 1)[0]
    body=re.sub(r'//[^\n]*', '', body)
    pins=[int(v) for v in re.findall(r'\b\d+\b', body)]
    if pins[:11] != [2,3,28,29,4,5,43,44,45,46,47]:
        raise ValueError('实际XIAO板包D0–D10映射与已核接口不一致')
    if pins[15:19] != [40,27,7,11]:
        raise ValueError('实际Sense板包IMU内部针脚不一致')


if __name__=='__main__':
    import sys
    check_variant(Path(sys.argv[1]).read_text())
else:
    Import('env')
    if env.subst('$BOARD') != 'xiaoblesense_adafruit':
        raise ValueError('F04只接受已核的XIAO Sense板包')
    framework=env.PioPlatform().get_package_dir('framework-arduinoadafruitnrf52-seeed')
    variant=Path(framework)/'variants/Seeed_XIAO_nRF52840_Sense/variant.cpp'
    check_variant(variant.read_text())
    project=Path(env.subst('$PROJECT_DIR'))
    files=[project/'platformio.ini',project/'verify_board.py',project/'sdk_patch.py',*sorted((project/'src').glob('*'))]
    files += [project.parent/'offline-f01'/name for name in ('v12_codec.c','v12_codec.h')]
    files += [project.parent/'dsp-f03'/name for name in ('v12_dsp.c','v12_dsp.h','coefficients.h')]
    hashes={str(p.relative_to(project.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    hashes['sdk/variant.cpp']=hashlib.sha256(variant.read_bytes()).hexdigest()
    bluefruit=Path(framework)/'libraries/Bluefruit52Lib/src/bluefruit.cpp'
    patched=patched_bluefruit(bluefruit.read_bytes())
    hashes['sdk/bluefruit.cpp.original']=hashlib.sha256(bluefruit.read_bytes()).hexdigest()
    hashes['sdk/bluefruit.cpp.patched']=hashlib.sha256(patched).hexdigest()
    signature=hashlib.sha256((json.dumps(hashes,sort_keys=True)+env.subst('$PIOENV')).encode()).hexdigest()
    generated=Path(env.subst('$BUILD_DIR'))/'generated'
    generated.mkdir(parents=True,exist_ok=True)
    content='#define MAKO_V12_BUILD_ID "'+signature[:16]+'"\n'
    header=generated/'v12_build_id.h'
    if not header.exists() or header.read_text()!=content: header.write_text(content)
    (generated/'build-inputs.json').write_text(json.dumps(dict(build_id=signature[:16],environment=env.subst('$PIOENV'),source_sha256=hashes),indent=2)+'\n')
    env.Append(CPPPATH=[str(generated)])
    sdk_copy=generated/'bluefruit.cpp'
    if not sdk_copy.exists() or sdk_copy.read_bytes()!=patched: sdk_copy.write_bytes(patched)
    def use_local_sdk(build_env,node):
        if Path(node.srcnode().get_abspath()).resolve()!=bluefruit.resolve():
            raise ValueError('构建匹配了未审查的Bluefruit源码: '+node.srcnode().get_abspath())
        return build_env.File(str(sdk_copy))
    env.AddBuildMiddleware(use_local_sdk,'*/Bluefruit52Lib/src/bluefruit.cpp')
