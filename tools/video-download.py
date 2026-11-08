# -*- coding: utf-8 -*-
"""通用视频下载：任何 yt-dlp 支持的站点，或者本地文件。

  python tools/video-download.py <url|本地路径> -o <目录>
  python tools/video-download.py https://www.bilibili.com/video/BVxxx -o work
  python tools/video-download.py D:\\clips\\demo.mp4 -o work

输出到 <目录>：
  video.mp4        视频
  subs.srt         字幕（如果站点有，比本地转写准且快）
  meta.json        标题、时长、上传者

## 为什么优先拿站点字幕

YouTube / B站 / 微博这类有 CC 字幕的站点，直接下字幕比本地跑
faster-whisper 强：
  · 准（人工字幕或平台 ASR）
  · 快（不用跑模型，几秒 vs 几十秒）
  · 有精确时间戳（转写的时间戳是估算的）

没字幕才回落到 transcribe-local.py。

## 格式选择

bv*[height<=1080]+ba/b —— 优先 1080p 以内最佳视频 + 最佳音频合并，
没有分离流就取最佳单流。竖屏视频（抖音/小红书）height 是短边，
所以 1080 的上限对小视频没影响。
"""
import json
import subprocess
import sys
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw)


def is_local(target):
    p = Path(target)
    return p.exists() and p.is_file()


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        sys.exit(__doc__)

    outdir = Path(arg('-o', 'work')).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    video = outdir / 'video.mp4'
    subs = outdir / 'subs.srt'
    meta = outdir / 'meta.json'

    # ── 本地文件：直接复制 ──
    if is_local(target):
        src = Path(target).resolve()
        print(f'本地文件: {src}')
        if src.suffix.lower() != '.mp4':
            r = run(['ffmpeg', '-v', 'error', '-y', '-i', str(src),
                     '-c', 'copy', str(video)])
            if r.returncode != 0:
                r = run(['ffmpeg', '-v', 'error', '-y', '-i', str(src),
                         '-c:v', 'libx264', '-c:a', 'aac', str(video)])
        else:
            import shutil
            shutil.copy2(src, video)
        meta.write_text(json.dumps({
            'source': str(src), 'title': src.stem, 'local': True,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'✓ {video}')
        return 0

    # ── 远程：yt-dlp ──
    print(f'下载 {target[:100]}')
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--no-warnings',
        '-f', 'bv*[height<=1080]+ba/b',
        '--merge-output-format', 'mp4',
        # 字幕：先试人工，再试自动
        '--write-subs', '--write-auto-subs',
        '--sub-langs', 'zh-Hans,zh-CN,zh,en.*',
        '--convert-subs', 'srt',
        '--no-playlist',
        '-o', str(outdir / 'video.%(ext)s'),
        '--print', 'after_move:filepath',
        '--print', 'title',
        target,
    ]
    r = run(cmd, timeout=900)
    out = (r.stdout or '').strip()
    err = (r.stderr or '').strip()

    if r.returncode != 0:
        print('下载失败：')
        print(err[-800:] if err else '(无输出)')
        print()
        print('常见原因：')
        print('  · 站点要登录 → 加 --cookies-from-browser chrome（但 Chrome 开着时会锁库）')
        print('  · 地区限制')
        print('  · yt-dlp 版本旧 → pip install -U yt-dlp')
        return 1

    lines = [l for l in out.split('\n') if l.strip()]
    title = lines[-1] if lines else ''

    # yt-dlp 可能输出什么后缀都不一定，找实际文件
    got = None
    for p in sorted(outdir.glob('video.*')):
        if p.suffix.lower() in ('.mp4', '.mkv', '.webm', '.flv'):
            got = p
            break

    if not got:
        print('没有下载到视频文件')
        print(out[-500:])
        return 1

    if got != video:
        try:
            got.replace(video)
        except Exception:
            video = got

    # 字幕：yt-dlp 会生成 video.zh-Hans.srt 这类名字
    srt_cands = sorted(outdir.glob('video*.srt'))
    if srt_cands:
        srt_cands[0].replace(subs)
        print(f'✓ 拿到站点字幕（比本地转写准）：{subs.name}')
    else:
        print('  站点没有字幕，后面要本地转写')

    size_mb = video.stat().st_size / 1048576
    meta.write_text(json.dumps({
        'source': target, 'title': title, 'local': False,
        'has_subs': subs.exists(), 'size_mb': round(size_mb, 2),
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'✓ {video}  ({size_mb:.1f} MB)')
    if title:
        print(f'  标题: {title[:70]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
