"""C08D V4 构建前脚本（PlatformIO pre:），做法同 firmware-f05-c05p/c05p_build.py。R01 的 firmware-f05 一个字节都不改：
读 ../firmware-f05/src/main.cpp（sha256 钉死），按 PATCHES 逐条替换（每个锚点必须正好出现一次），写到构建目录。
P44b 脚表（v12/c08-p44b-xiao-adapter-mini-20261027/pin-table.csv）：D7 CS_A、D6 DRDY_A、D2 RESET、D4 PWDN、D8/9/10 SPI 与 R01 相同；
D0 是 CS_B、D3 是 START（10k 下拉）、D5 是 DRDY_B（P48X 背面不贴，悬空）、D1 不接（CLKSEL 由 V4 R17 下拉，用 X1 外部时钟）。
V4 的 ±2.5 V 由 XIAO 3V3 经 LM27762 一直供着，没有电源使能和电源检测脚。"""
from pathlib import Path
import hashlib
import json
import re
import sys

F05_MAIN_SHA256 = '12afcd92fa669c12944071b31a3402b8528c043d0a71754d558ec88da703a9e8'
PATCHES = [
    # D0 在 V4 上是 CS_B：不能当模拟电源使能来回拉，开机起一直拉高（第二颗不选中）。
    ('spi_on=true;digitalWrite(D0,HIGH);}', 'spi_on=true;}'),
    ('  else {digitalWrite(D0,LOW);if(spi_on)', '  else {if(spi_on)'),
    (' void clocksel(bool on) override {digitalWrite(D1,on?HIGH:LOW);}',
     ' void clocksel(bool) override {} // V4：CLKSEL 由 R17 下拉，D1 不接'),
    # V4 没有电源检测脚（D3 是 START、D5 是 DRDY_B）：照读会判电源故障停机。是否上电只能靠台架实测，硬件锁不变。
    ('  // 内部0.6V参考×6为3.6V量程，再乘板上1:4分压；只作粗筛，不能替代台架。\n'
     '  unsigned raw=analogRead(D3);float avdd=float(raw)*14.4f/4095.0f;\n'
     '  return digitalRead(D5)==LOW && avdd>=4.6f && avdd<=5.4f;',
     '  return true; // V4：模拟电源常开、无检测脚，只能靠台架实测'),
    ('  if(digitalRead(D5)!=LOW)ads.stop(v12::Fault::Rails);\n  else if(count!=used_edge) {',
     '  if(count!=used_edge) { // V4：D5 是 DRDY_B，不是电源好信号'),
    # D3（START）保持低：采集用 START 命令（0x08），START 脚必须为低。D0 拉高；D1 不驱动；D5 下拉防悬空。
    (' const uint8_t outputs[]={D0,D1,D2,D4,D7,D8,D10};',
     ' digitalWrite(D0,HIGH); pinMode(D0,OUTPUT);\n const uint8_t outputs[]={D2,D3,D4,D7,D8,D10};'),
    (' pinMode(D5,INPUT); pinMode(D6,INPUT);', ' pinMode(D5,INPUT_PULLDOWN); pinMode(D6,INPUT);'),
    ('\\"clock_resolution_us\\":1}"', '\\"clock_resolution_us\\":1,\\"board\\":\\"V4\\"}"'),
]


def patch_main(text):
    if hashlib.sha256(text.encode()).hexdigest() != F05_MAIN_SHA256:
        raise ValueError('F05 main.cpp 已变：重新审查 V4 补丁后再更新 F05_MAIN_SHA256')
    for before, after in PATCHES:
        if text.count(before) != 1:
            raise ValueError('补丁锚点不是正好一处：' + before[:60])
        text = text.replace(before, after)
    return '// 由 v4_build.py 从 firmware-f05/src/main.cpp 生成，勿手改\n' + text


if __name__ == '__main__':
    # 自测：真实 F05 main.cpp 能打完全部补丁；V4 上不许出现的脚用法一处都不剩；改过的 main.cpp 被拒。
    f05 = Path(__file__).resolve().parent.parent / 'firmware-f05'
    src = (Path(sys.argv[1]) if len(sys.argv) > 1 else f05 / 'src/main.cpp').read_text()
    out = patch_main(src)
    for banned in ('digitalWrite(D0,LOW)', 'digitalWrite(D1', 'pinMode(D1', 'analogRead(D3)', 'digitalRead(D5)', 'D0,D1'):
        assert banned not in out, banned
    # 每条补丁的结果都要在（复核 P2：原先去掉第 1、7、8 条自测仍过）
    for _, after in PATCHES:
        assert after in out, after[:60]
    assert out.count('D0') == 2, 'D0 只允许在 hold_afe_off 里拉高（一行两处）'
    ads = (f05 / 'src/ads1298.cpp').read_text()
    # WCT1/WCT2（0x18/0x19）在 regs[26]={} 里为 0，写入循环到 0x19 并逐个回读——原厂固件残留的 WCT1=0x60 会被清掉。
    assert 'uint8_t regs[26]={};' in ads and 'for(uint8_t a=1;a<=0x19;++a)' in ads and 'regs[0x18]' not in ads and 'regs[24]' not in ads
    try:
        patch_main(src.replace('D1', 'D11', 1)); raise SystemExit('改过的 main.cpp 没被拒绝')
    except ValueError:
        pass
    print(f'v4_build 自测通过：{len(PATCHES)} 处补丁全部命中，D0/D1/D3/D5 无 R01 用法残留，WCT 清零，改过的 main.cpp 被拒')
elif 'Import' in globals():   # PlatformIO（SCons）执行时才有 Import
    Import('env')
    project = Path(env.subst('$PROJECT_DIR'))
    f05 = project.parent / 'firmware-f05'
    sys.path.insert(0, str(f05))
    from sdk_patch import patched_bluefruit
    if env.subst('$BOARD') != 'xiaoblesense_adafruit':
        raise ValueError('V4 只接受已核的 XIAO Sense 板包（同 F05）')
    framework = Path(env.PioPlatform().get_package_dir('framework-arduinoadafruitnrf52-seeed'))
    variant = framework / 'variants/Seeed_XIAO_nRF52840_Sense/variant.cpp'
    # 同 F05 verify_board.check_variant（不能 import：它在模块级跑 F05 自己的构建步骤）
    body = re.sub(r'//[^\n]*', '', variant.read_text().split('g_ADigitalPinMap[]', 1)[1].split('{', 1)[1].split('}', 1)[0])
    pins = [int(v) for v in re.findall(r'\b\d+\b', body)]
    if pins[:11] != [2, 3, 28, 29, 4, 5, 43, 44, 45, 46, 47]:
        raise ValueError('实际XIAO板包D0–D10映射与已核接口不一致')
    if pins[15:19] != [40, 27, 7, 11]:
        raise ValueError('实际Sense板包IMU内部针脚不一致')
    generated = Path(env.subst('$BUILD_DIR')) / 'generated'
    generated.mkdir(parents=True, exist_ok=True)
    main_v4 = patch_main((f05 / 'src/main.cpp').read_text())
    out = generated / 'f05_main_v4.cpp'
    if not out.exists() or out.read_text() != main_v4: out.write_text(main_v4)

    files = [project / 'platformio.ini', project / 'v4_build.py', *sorted((project / 'src').glob('*')),
             f05 / 'sdk_patch.py', f05 / 'verify_board.py', *sorted((f05 / 'src').glob('*'))]
    hashes = {str(p.relative_to(project.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    hashes['sdk/variant.cpp'] = hashlib.sha256(variant.read_bytes()).hexdigest()
    for name in ('cores/nRF5/wiring.c', 'cores/nRF5/nordic/nrfx_config.h', 'libraries/SPI/SPI.cpp'):
        hashes['sdk/resource/' + name] = hashlib.sha256((framework / name).read_bytes()).hexdigest()
    nrfx = (framework / 'cores/nRF5/nordic/nrfx_config.h').read_text()
    if not re.search(r'^#define NRFX_TIMER2_ENABLED 0$', nrfx, re.M):
        raise ValueError('SDK已启用TIMER2驱动，不能与采集计时器共用')
    bluefruit = framework / 'libraries/Bluefruit52Lib/src/bluefruit.cpp'
    patched = patched_bluefruit(bluefruit.read_bytes())
    hashes['sdk/bluefruit.cpp.original'] = hashlib.sha256(bluefruit.read_bytes()).hexdigest()
    hashes['sdk/bluefruit.cpp.patched'] = hashlib.sha256(patched).hexdigest()
    defines = dict(item for item in env.ParseFlags(env.get('BUILD_FLAGS', [])).get('CPPDEFINES', []) if isinstance(item, (tuple, list)))
    settings = dict(board='V4', fs_Hz=int(defines['MAKO_V12_FS']), spi_Hz=int(defines.get('MAKO_V12_SPI_HZ', 2000000)),
                    imu_enabled=int(defines.get('MAKO_V12_IMU_ENABLED', 0)))
    signature = hashlib.sha256((json.dumps(dict(source=hashes, settings=settings), sort_keys=True) + env.subst('$PIOENV')).encode()).hexdigest()
    content = '#define MAKO_V12_BUILD_ID "' + signature[:16] + '"\n'
    header = generated / 'v12_build_id.h'
    if not header.exists() or header.read_text() != content: header.write_text(content)
    (generated / 'build-inputs.json').write_text(json.dumps(dict(build_id=signature[:16], environment=env.subst('$PIOENV'),
                                                                 source_sha256=hashes, **settings), indent=2) + '\n')
    env.Append(CPPPATH=[str(generated), str(f05 / 'src'), str(project / 'src')])
    sdk_copy = generated / 'bluefruit.cpp'
    if not sdk_copy.exists() or sdk_copy.read_bytes() != patched: sdk_copy.write_bytes(patched)

    def use_local_sdk(build_env, node):
        if Path(node.srcnode().get_abspath()).resolve() != bluefruit.resolve():
            raise ValueError('构建匹配了未审查的Bluefruit源码: ' + node.srcnode().get_abspath())
        return build_env.File(str(sdk_copy))
    env.AddBuildMiddleware(use_local_sdk, '*/Bluefruit52Lib/src/bluefruit.cpp')
