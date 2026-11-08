# -*- coding: utf-8 -*-
"""检查字幕切换点是否对得上实际说话位置。

## 为什么要查

上一轮把字幕按「字数比例」拆成了 1.5 秒一条。
但人说话不是匀速的 —— 停顿、重音都会让实际节奏偏移。

如果字幕换早了或换晚了，观众看的时候会觉得别扭
（字幕在说上一句，耳朵听到的是下一句）。

## 怎么查

1. 按 50ms 切片算音频能量
2. 找出能量明显下降的位置（说话停顿）
3. 对比字幕切换点：如果字幕在「说话中间」切换，说明切早了或切晚了

理想情况：字幕切换点应该落在停顿附近（±0.3 秒内）。
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def load_audio(path, sr=16000):
    """用 ffmpeg 解码成单声道 float，避免依赖 librosa。"""
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path),
         '-ar', str(sr), '-ac', '1', '-f', 'f32le', '-'],
        capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32), sr


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()

    # 用纯配音，不用 score.wav（有 BGM 测不准）
    # 优先用 --audio 指定的纯配音（score.wav 有 BGM，能量测不准）
    ap = arg('--audio')
    wav = Path(ap) if ap else None
    if not wav or not wav.exists():
        for name in ['vo.wav', 'voice.wav', 'pure.wav']:
            q = proj / 'audio' / name
            if q.exists():
                wav = q
                break
    if not wav:
        wav = proj / 'audio' / 'score.wav'
        print('⚠ 用的是 score.wav（含 BGM），能量检测会不准')
        print('  建议先拼一份纯配音，用 --audio 指定')
    print(f'音频: {wav.name}')

    sp = proj / 'audio' / 'subs.json'
    subs = json.loads(sp.read_text(encoding='utf-8'))
    subs = subs if isinstance(subs, list) else subs.get('subs', [])

    audio, sr = load_audio(wav)
    if len(audio) == 0:
        sys.exit('解码失败')

    # 50ms 一帧算 RMS
    win = int(sr * 0.05)
    n = len(audio) // win
    rms = np.array([
        float(np.sqrt(np.mean(audio[i * win:(i + 1) * win] ** 2)))
        for i in range(n)
    ])
    if rms.max() > 0:
        rms = rms / rms.max()

    # 找出「能量低谷」位置（说话停顿）
    thr = float(arg('--thr', '0.06'))
    low = rms < thr
    pauses = []
    i = 0
    while i < len(low):
        if low[i]:
            j = i
            while j < len(low) and low[j]:
                j += 1
            # 至少 0.12 秒才算停顿
            if (j - i) * 0.05 >= 0.12:
                pauses.append(((i + j) / 2 * 0.05, (j - i) * 0.05))
            i = j
        else:
            i += 1

    print(f'检测到 {len(pauses)} 处停顿（>0.12s）')
    print()

    # 字幕切换点 = 每条字幕的 b（结束）也是下一条的 a
    switches = [s['b'] for s in subs[:-1]]
    print(f'{len(subs)} 条字幕，{len(switches)} 个切换点')
    print()

    bad = 0
    for k, t in enumerate(switches):
        # 找最近的停顿
        if pauses:
            near = min(pauses, key=lambda p: abs(p[0] - t))
            dist = abs(near[0] - t)
        else:
            dist = 999
        ok = dist <= 0.35
        if not ok:
            bad += 1
        mark = '✓' if ok else '✗'
        # 该时刻的能量
        idx = int(t / 0.05)
        e = rms[idx] if idx < len(rms) else 0
        print(f'  {mark} {t:5.2f}s  能量 {e:.2f}  离最近停顿 {dist:.2f}s')

    print()
    if bad:
        print(f'✗ {bad}/{len(switches)} 个切换点落在说话中间（不在停顿上）')
        print('  这说明字幕换早或换晚了 —— 观众会觉得字幕和声音不同步')
    else:
        print(f'✓ 全部 {len(switches)} 个切换点都落在停顿附近')


if __name__ == '__main__':
    main()
