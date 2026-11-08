# -*- coding: utf-8 -*-
"""检查循环接缝：BGM 的首尾是否电平接近。

## 为什么

BGM 只有 10~16 秒，视频 34.8 秒，用 aloop 循环。
如果曲子首部和尾部电平差很大（比如头是 -0.4 dB 满电平、尾是静音），
循环点会有一个突然的音量跳变 —— 人耳听起来就是一个"咔"或"嘭"。

## 判据

首尾 RMS 差 < 6 dB 的话，接缝基本听不出来。
差得多就需要在循环点加交叉淡化。
"""
import subprocess
from pathlib import Path

import numpy as np

BGM_DIR = Path('D:/DSH/achun/video-xiaobai/audio/bgm')
FILES = ['Carefree.mp3', 'Life_of_Riley.mp3', 'Fluffing_a_Duck.mp3', 'Wallpaper.mp3']


def load(path, sr=16000):
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path),
         '-ar', str(sr), '-ac', '1', '-f', 'f32le', '-'],
        capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32), sr


def rms_db(x):
    if len(x) == 0:
        return -99.0
    r = float(np.sqrt(np.mean(x ** 2)))
    return 20 * np.log10(max(r, 1e-9))


def main():
    print(f'{"BGM":24s} {"头部 RMS":>10s} {"尾部 RMS":>10s} {"差值":>8s}  判断')
    print('-' * 72)
    for name in FILES:
        p = BGM_DIR / name
        if not p.exists():
            print(f'{name:24s} 不存在')
            continue
        a, sr = load(p)
        if len(a) < sr:
            print(f'{name:24s} 太短')
            continue
        # 各取 50ms
        n = int(sr * 0.05)
        head = rms_db(a[:n])

        # 找最后一段有声的地方（尾部可能有静音填充）
        win = int(sr * 0.02)
        m = len(a) // win
        rms = np.array([
            float(np.sqrt(np.mean(a[i * win:(i + 1) * win] ** 2)))
            for i in range(m)
        ])
        loud = np.where(rms > rms.max() * 0.05)[0]
        last_loud = (loud[-1] + 1) * 0.02 if len(loud) else 0
        dur = len(a) / sr

        # 如果尾部有静音填充，用最后一个有声点算
        tail_trim = rms_db(a[max(0, int(last_loud * sr) - n):int(last_loud * sr)])
        real_diff = abs(head - tail_trim)

        verdict = '接缝不明显' if real_diff < 6 else '需要交叉淡化'
        print(f'{name:24s} {head:9.1f}dB {tail_trim:9.1f}dB {real_diff:7.1f}dB  {verdict}')
        if real_diff >= 6:
            print(f'{"":24s} 有声部分到 {last_loud:.2f}s / 全长 {dur:.2f}s')


if __name__ == '__main__':
    main()
