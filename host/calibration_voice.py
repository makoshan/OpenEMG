"""校准口令只用 Mac 本地语音；先合成短口令，录制开始时直接播放。"""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile
import time

NAMES = {
    'mouse_rest': '保持放松', 'mouse_index': '食指轻捏拇指',
    'mouse_middle': '中指轻捏拇指', 'mouse_up': '拇指上滑',
    'mouse_down': '拇指下滑', 'mouse_left': '拇指左滑',
    'mouse_right': '拇指右滑', 'mouse_side': '拇指侧点',
    'mouse_swipe': '拇指拨一下',      # 2026-10-10 Mako 定：上 / 下 / 左合成一类（八路电极分不开三个方向，留一 0.47–0.67）
    'ai_rest': '保持放松', 'ai_summon': '中指轻捏拇指',
    'ai_up': '拇指上滑', 'ai_down': '拇指下滑', 'ai_left': '拇指左滑', 'ai_right': '拇指右滑',
}


class CalibrationVoice:
    def __init__(self, stopped):
        if sys.platform != 'darwin':
            raise ValueError('校准语音需要 Mac 本地语音服务')
        self.stopped = stopped
        self.tmp = tempfile.TemporaryDirectory(prefix='yuanli-calibration-voice-')
        self.children = []

    def _run(self, args, timeout=15):
        # 不用 shell；只终止本次口令创建的子进程。停下和合成失败均不能继续录。
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.children.append(p)
        end = time.monotonic() + timeout
        while p.poll() is None:
            if self.stopped() or time.monotonic() >= end:
                p.terminate()
                p.wait(timeout=2)
                raise ValueError('校准口令已取消或超时，未开始录制')
            time.sleep(.05)
        if p.returncode:
            raise ValueError('校准语音播放失败，请检查 Mac 声音输出后重试')

    def _audio(self, text):
        # 口令不含用户数据。按文字/语音/语速缓存，避免每条录制重启慢速合成。
        cache = Path.home() / '.cache' / 'yuanli-calibration-voice'
        cache.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(('Tingting:220:' + text).encode()).hexdigest()
        path = cache / f'{key}.aiff'
        if path.is_file() and path.stat().st_size > 4096:
            return path
        pending = Path(self.tmp.name) / f'{key}.aiff'
        self._run(['/usr/bin/say', '-v', 'Tingting', '-r', '220', '-o', str(pending), text], timeout=60)
        if not pending.is_file() or pending.stat().st_size <= 4096:
            raise ValueError('校准口令合成失败，未开始录制')
        # 合成成功才发布缓存；取消/超时生成的半文件绝不复用。
        pending.replace(path)
        return path

    def prepare(self, label):
        self.files = {key: self._audio(text) for key, text in [('go', '开始'), ('rest', '保持放松'), ('release', '松开')]}
        self.files['prepare'] = self._audio(f'下一条，{NAMES[label]}。先放松，倒数结束听到开始再做。')
        self.cue('prepare')

    def cue(self, key, wait=True):
        # AIFF 已合成，避免在两秒动作窗开始时才启动文字转语音。
        # YUANLI_VOICE=off：只合成不出声（假手环试用台 / 旁边有人时用），流程和时序照旧。
        if os.environ.get('YUANLI_VOICE') == 'off': return
        if wait: self._run(['/usr/bin/afplay', str(self.files[key])]); return
        # wait=False：「开始」口令要和录制窗同时起。阻塞播完再开录，用户听到就动，窗口只录到动作尾巴
        #（2026-10-10 第 10 次佩戴 21 条每条开窗即满幅、1.4 s 衰减，留一 35%；第 5 / 7 次无语音时脉冲在 0.6–1.2 s，81% / 86%）。
        self.children.append(subprocess.Popen(['/usr/bin/afplay', str(self.files[key])], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    def close(self):
        for p in self.children:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=2)
        self.tmp.cleanup()


def warmup():
    """安装/交付时预合成固定中文口令，不播放、不连接设备。"""
    from concurrent.futures import ThreadPoolExecutor
    texts = ['开始', '保持放松', '松开'] + [f'下一条，{name}。先放松，倒数结束听到开始再做。' for name in NAMES.values()]
    def synth(text):
        voice = CalibrationVoice(lambda: False)
        try: return str(voice._audio(text))
        finally: voice.close()
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(synth, texts))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--warmup', action='store_true')
    args = parser.parse_args()
    if args.warmup: print(f'本地校准语音缓存：{len(warmup())} 条就绪；未播放、未采集')
