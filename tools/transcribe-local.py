# -*- coding: utf-8 -*-
"""本地转写（faster-whisper），并从文本里找 GitHub 仓库地址。

  python tools/transcribe-local.py <视频|音频> --out out.json [--model small]
  python tools/transcribe-local.py <视频> --find-repo      # 只打印找到的仓库

为什么不用 whisperx：whisperx 的 alignment 模型经常加载失败，faster-whisper
只做识别不做对齐，胜在稳、快、零依赖网络。
"""
import sys, re, json, subprocess, tempfile, os
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


REPO_PATTERNS = [
    r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',
    r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*(?:这个|的)?\s*(?:仓库|项目|repo)',
    r'(?:仓库|项目|repo)\s*(?:叫|是|：|:)?\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',
]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        sys.exit(__doc__)
    model_size = arg('--model', 'small')
    out = arg('--out')

    src = Path(src)
    if not src.exists():
        sys.exit(f'找不到 {src}')

    # 用 ffmpeg 直接吐 f32le，走 numpy 喂模型。
    # faster-whisper 1.2.1 依赖的 PyAV 在部分环境里 open() 签名不兼容，
    # 绕开文件读取就能避开（报错原文：open() got an unexpected keyword argument 'metadata_errors'）。
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(src),
                          '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    print(f'音频: {len(audio)/16000:.1f}s')

    from faster_whisper import WhisperModel
    print(f'加载模型 {model_size}（首次会下载）…')
    model = WhisperModel(model_size, device='cpu', compute_type='int8')

    print('转写中…')
    segments, info = model.transcribe(audio, language='zh', vad_filter=True,
                                      beam_size=5, best_of=5)
    segs = []
    for s in segments:
        segs.append({'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip()})
        print(f'  [{s.start:6.2f}-{s.end:6.2f}] {s.text.strip()}')

    full = ''.join(s['text'] for s in segs)
    chars = len(re.sub(r'\s', '', full))
    dur = segs[-1]['end'] if segs else 0
    print(f'\n共 {chars} 字 / {dur:.1f}s = {chars/max(dur,0.1):.2f} 字/秒')

    # 找仓库
    repos = []
    for pat in REPO_PATTERNS:
        for m in re.finditer(pat, full, re.I):
            r = m.group(1).strip('/.')
            if '/' not in r:
                continue
            if r.lower().startswith(('http', 'www')):
                continue
            if r not in repos:
                repos.append(r)

    if repos:
        print('\n=== 找到的仓库 ===')
        for r in repos:
            print(f'  https://github.com/{r}')
    else:
        print('\n=== 没找到 github owner/repo 形式的地址 ===')
        # 退一步：列出文本里出现的英文专有名词
        names = re.findall(r'[A-Za-z][A-Za-z0-9_.-]{2,}', full)
        seen, uniq = set(), []
        for n in names:
            if n.lower() in seen:
                continue
            seen.add(n.lower())
            uniq.append(n)
        if uniq:
            print('文本里的英文词（可能是工具名）：')
            print('  ' + ', '.join(uniq[:40]))

    if out:
        data = {'source': str(src), 'chars': chars, 'duration': round(dur, 2),
                'rate': round(chars / max(dur, 0.1), 2), 'segments': segs,
                'full': full, 'repos': repos}
        Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'\n写到 {out}')



if __name__ == '__main__':
    main()
