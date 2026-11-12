"""对实际生成的固件状态机做边界替身测试，不接设备。"""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import shutil
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dout_build',HERE/'build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
stage=b.stage('platformio/toolchain-gccarmnoneeabi@1.120301.0')
with tempfile.TemporaryDirectory(prefix='r01-flow-') as tmp:
    tmp=Path(tmp);shutil.copytree(stage/'src',tmp/'src')
    for name in ('timebase_board.h','bench_release.h','v12_build_id.h'):
        shutil.copyfile(HERE/'tests/stubs'/name,tmp/'src'/name)
    common=['-I'+str(HERE/'tests/stubs'),'-I'+str(tmp/'src')]
    objs=[]
    for name in ('v12_codec.c','v12_stream.c','v12_dsp.c'):
        obj=tmp/(name+'.o');subprocess.run(['cc','-std=c11',*common,'-c',str(tmp/'src'/name),'-o',str(obj)],check=True);objs.append(str(obj))
    exe=tmp/'flow'
    subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Wno-unused-function',*common,str(HERE/'tests/test_flow.cpp'),str(tmp/'src/ads1298.cpp'),*objs,'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
