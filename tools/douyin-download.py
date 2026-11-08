# -*- coding: utf-8 -*-
"""下载抖音视频（直接提取播放地址，不依赖 yt-dlp）。

抖音页面里视频地址藏在 RENDER_DATA（URL 编码的 JSON）或内联 JSON 里。
本脚本用 Playwright 打开页面，把 mp4 直链捞出来下载。

  python tools/douyin-download.py <视频URL 或 ID> -o <输出目录>
  python tools/douyin-download.py 7662716941353749775 -o douyin/dl
"""
import contextlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def find_play_urls(html):
    """从页面 HTML 里捞所有可能的 mp4 地址。"""
    urls = []
    # 1. RENDER_DATA
    m = re.search(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            raw = urllib.parse.unquote(m.group(1))
            urls += re.findall(r'"(https?:\\?/\\?/[^"]+?\.mp4[^"]*)"', raw)
            urls += re.findall(r'https?:\\?/\\?/[^\s"\\]+?\.mp4[^\s"\\]*', raw)
        except Exception:
            pass
    # 2. 内联 JSON / 通用正则
    urls += re.findall(r'"(https?://[^"]+?\.mp4[^"]*)"', html)
    urls += re.findall(r'https?://[^\s"\'\\<>]+?\.mp4[^\s"\'\\<>]*', html)

    # 清理转义
    out = []
    for u in urls:
        u = u.replace('\\u002F', '/').replace('\\/', '/').replace('\\u0026', '&')
        u = u.rstrip('\\')
        if not u.startswith('http'):
            continue
        # 去水印：playwm → play
        u = u.replace('/playwm/', '/play/').replace('playwm', 'play')
        out.append(u)

    # 去重，按出现顺序
    seen, uniq = set(), []
    for u in out:
        key = u.split('?')[0]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(u)
    return uniq


def download(url, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url)
    req.add_header('User-Agent', UA)
    req.add_header('Referer', 'https://www.douyin.com/')
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        got = 0
        while True:
            buf = r.read(1 << 20)
            if not buf:
                break
            f.write(buf)
            got += len(buf)
            if total:
                print(f'\r  {got/1048576:.1f}/{total/1048576:.1f} MB', end='')
    print()
    return dest


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        sys.exit(__doc__)
    outdir = Path(arg('-o', 'douyin/dl')).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    m = re.search(r'/video/(\d{15,25})', target)
    vid = m.group(1) if m else target
    url = target if target.startswith('http') else f'https://www.douyin.com/video/{vid}'

    print(f'打开 {url[:90]}')
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=True,
                              args=['--disable-blink-features=AutomationControlled'])
        ctx = b.new_context(user_agent=UA, viewport={'width': 1280, 'height': 900},
                            locale='zh-CN', extra_http_headers={'Referer': 'https://www.douyin.com/'})
        pg = ctx.new_page()
        with contextlib.suppress(Exception):
            pg.goto(url, wait_until='domcontentloaded', timeout=45000)
        pg.wait_for_timeout(5000)
        with contextlib.suppress(Exception):
            pg.wait_for_selector('video', timeout=8000)
        html = pg.content()
        title = pg.title()
        # 页面上的 video 标签 src 也可能是直链
        vids = pg.eval_on_selector_all('video', "els => els.map(e => e.src || e.currentSrc).filter(Boolean)")
        b.close()

    print(f'标题: {title[:70]}')

    urls = find_play_urls(html)
    for v in vids:
        if v.startswith('http') and v not in urls:
            urls.insert(0, v)

    if not urls:
        sys.exit('× 页面里没找到 mp4 地址（可能被风控，或页面结构变了）')

    print(f'找到 {len(urls)} 个候选地址，按码率排序后下载最大的：')
    for i, u in enumerate(urls[:5]):
        print(f'  {i+1}. {u[:110]}')

    # 优先选 URL 里没 water 标记、且看起来完整的
    dest = outdir / f'{vid}.mp4'
    last_err = None
    for u in urls[:6]:
        try:
            print(f'\n下载 {u[:90]}')
            download(u, dest)
            if dest.exists() and dest.stat().st_size > 200_000:
                size = dest.stat().st_size / 1048576
                print(f'✓ {dest}  ({size:.1f} MB)')
                # 探测规格
                try:
                    info = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                           'format=duration', '-show_entries',
                                           'stream=width,height,r_frame_rate',
                                           '-of', 'default=nw=1', str(dest)],
                                          capture_output=True, text=True).stdout
                    print(info.strip())
                except Exception:
                    pass
                print(f'\nTITLE={title}')
                return
            else:
                print('  文件太小，换下一个')
        except Exception as e:
            last_err = e
            print(f'  失败：{str(e)[:80]}')

    sys.exit(f'× 全部失败：{last_err}')


if __name__ == '__main__':
    main()
