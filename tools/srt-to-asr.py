# -*- coding: utf-8 -*-
"""SRT → asr.json，让站点字幕能直接顶替本地转写。

  python tools/srt-to-asr.py <srt> -o asr.json

产物格式和 transcribe-local.py 的输出一致：
  {source, chars, duration, rate, segments: [{start, end, text}], full, repos}

为什么需要：YouTube / B站 的 CC 字幕是人工或平台 ASR 做的，
比本地 faster-whisper 准，而且有精确时间戳（本地转写的是估算）。
"""
import json
import re
import sys
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def srt_time(s):
    m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)', s)
    if not m:
        return 0.0
    g = [int(x) for x in m.groups()]
    return g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000


def parse_srt(path):
    txt = open(path, encoding='utf-8', errors='ignore').read().strip()
    out = []
    for block in txt.split('\n\n'):
        lines = [line for line in block.split('\n') if line.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r'(.+?)\s*-->\s*(.+)', lines[1])
        if not m:
            continue
        text = ''.join(lines[2:])
        # YouTube 自动字幕会带时间标记，去掉
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            out.append((srt_time(m.group(1)), srt_time(m.group(2)), text))
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        sys.exit(__doc__)

    segs = parse_srt(src)
    if not segs:
        sys.exit('字幕是空的')

    # 合并过碎的片段：YouTube 自动字幕经常一句切成 5 段
    merged = []
    for a, b, t in segs:
        if merged and a - merged[-1]['end'] < 1.2 and \
                len(merged[-1]['text']) + len(t) < 40:
            merged[-1]['end'] = b
            merged[-1]['text'] += t
        else:
            merged.append({'start': round(a, 2), 'end': round(b, 2), 'text': t})

    full = ''.join(m['text'] for m in merged)
    chars = len(re.sub(r'\s', '', full))
    dur = merged[-1]['end'] if merged else 0

    data = {
        'source': str(src),
        'from': 'srt',
        'chars': chars,
        'duration': round(dur, 2),
        'rate': round(chars / max(dur, 0.1), 2),
        'segments': merged,
        'full': full,
        'repos': [],
    }

    out = arg('-o')
    if out:
        Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'✓ {out}  {len(merged)} 段 / {chars} 字 / {dur:.1f}s')
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
