"""单通道（Cheez + ESP32-S3）采集入口：原样跑 host/emg_web.py，和 PrintThings「单通道」同一个后端和 /guide 页面。
包内 Python 用 -I 启动，不会把脚本目录放进 sys.path，所以这里补上 host 目录；再加父进程看门狗，App 被强杀时不留孤儿占串口。
文件名不带 emg8- 前缀：只属于原力手环 App，不同步到 vibe-hw。"""
import argparse
import os
from pathlib import Path
import runpy
import sys
import threading
import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--firmware-root', required=True)
    args, remaining = parser.parse_known_args()
    root = Path(args.firmware_root).resolve()
    sys.path.insert(0, str(root))
    parent = os.getppid()
    def watch_parent():
        while os.getppid() == parent: time.sleep(1)
        os._exit(0)
    threading.Thread(target=watch_parent, daemon=True).start()
    sys.argv = [str(root / 'emg_web.py'), *remaining]
    runpy.run_path(sys.argv[0], run_name='__main__')
