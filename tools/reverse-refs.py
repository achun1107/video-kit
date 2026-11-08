# -*- coding: utf-8 -*-
"""批量逆向参考视频：解析链接 → 下载 → 转写 → 抽帧。

  python tools/reverse-refs.py --out refs
  python tools/reverse-refs.py --out refs --only ajin

对每个参考视频产出：
  refs/<name>/video.mp4
  refs/<name>/asr.json
  refs/<name>/frames/*.png      （每 3 秒一帧，给视觉分析用）
  refs/<name>/info.json         （标题、时长、点赞）
"""
import json
import subprocess
import sys
from pathlib import Path

# 四个参考视频
REFS = [
    ('ajin',      'https://v.douyin.com/G3S2LdSYXNg/', '阿津AI库',   '提示词开源工具'),
    ('weitu',     'https://v.douyin.com/cOCY9cWhTow/', '喂兔',       'AI 操控电脑'),
    ('ganhuoju',  'https://v.douyin.com/BwpxFPQc5Fw/', '开源工具干货局', 'Scrapling 爬虫'),
    ('xiaokai',   'https://v.douyin.com/Wmzqm4hcZJc/', 'AI小凯',     '一天一个神奇网站'),
]

TOOLS = Path(__file__).resolve().parent


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw)


def main():
    outroot = Path(arg('--out', 'refs')).resolve()
    outroot.mkdir(parents=True, exist_ok=True)
    only = arg('--only')

    for name, url, author, topic in REFS:
        if only and only != name:
            continue

        d = outroot / name
        d.mkdir(exist_ok=True)
        print(f'\n{"="*60}')
        print(f'{name}  {author} — {topic}')
        print('='*60)

        # 1) 解析链接
        rj = d / 'resolve.json'
        if not rj.exists():
            print('  解析 …')
            run([sys.executable, str(TOOLS / 'douyin-resolve.py'), url,
                 '--json', str(rj), '--max', '3'])
        try:
            info = json.loads(rj.read_text(encoding='utf-8'))
        except Exception:
            print('  × 解析失败')
            continue

        kind = info.get('kind', '?')
        videos = info.get('videos') or []
        print(f'  类型 {kind}，视频 {len(videos)} 条')

        if not videos:
            print('  × 没解析出视频')
            continue

        vid = videos[0]['id']

        # 2) 下载
        mp4 = d / 'video.mp4'
        if not mp4.exists():
            print(f'  下载 {vid} …')
            run([sys.executable, str(TOOLS / 'douyin-download.py'), vid,
                 '-o', str(d)])
            # douyin-download 存成 <id>.mp4
            got = d / f'{vid}.mp4'
            if got.exists():
                got.replace(mp4)
        if not mp4.exists():
            print('  × 下载失败')
            continue

        # 3) 转写
        asr = d / 'asr.json'
        if not asr.exists():
            print('  转写 …')
            run([sys.executable, str(TOOLS / 'transcribe-local.py'), str(mp4),
                 '--model', arg('--model', 'small'), '--out', str(asr)])
        try:
            a = json.loads(asr.read_text(encoding='utf-8'))
            print(f'  {a.get("chars",0)} 字 / {a.get("duration",0)}s '
                  f'/ {a.get("rate",0)} 字每秒')
        except Exception:
            print('  × 转写失败')

        # 4) 抽帧（每 3 秒一张，给视觉分析）
        fdir = d / 'frames'
        fdir.mkdir(exist_ok=True)
        if not list(fdir.glob('*.png')):
            print('  抽帧 …')
            try:
                dur = json.loads(asr.read_text(encoding='utf-8')).get('duration', 30)
            except Exception:
                dur = 30
            times = [round(x * 3.0, 1) for x in range(int(dur / 3) + 1)]
            for t in times:
                p = fdir / f'f_{t:05.2f}.png'
                if p.exists():
                    continue
                run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t),
                     '-i', str(mp4), '-frames:v', '1',
                     '-vf', 'scale=480:-1', str(p)])
            n = len(list(fdir.glob('*.png')))
            print(f'  {n} 帧')

        # 5) 记录
        (d / 'info.json').write_text(json.dumps({
            'name': name, 'url': url, 'author': author, 'topic': topic,
            'kind': kind, 'video_id': vid,
            'title': info.get('title', ''),
        }, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n{"="*60}')
    print(f'完成，产物在 {outroot}')
    for name, _, author, topic in REFS:
        d = outroot / name
        if not d.exists():
            continue
        ok = (d / 'video.mp4').exists() and (d / 'asr.json').exists()
        nf = len(list((d / 'frames').glob('*.png'))) if (d / 'frames').exists() else 0
        print(f'  {"✓" if ok else "✗"} {name:10s} {author:10s} '
              f'{topic:16s} 帧 {nf}')


if __name__ == '__main__':
    main()
