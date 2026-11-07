# -*- coding: utf-8 -*-
"""批量截站点页面，给视频当素材（多截图叠压用）。

  python tools/batch-shot.py https://supercli.site -o assets/site
  python tools/batch-shot.py <base> -o <dir> --paths /,/start/,/catalog

输出：
  <dir>/page_00.png ...   每页一张
  <dir>/index.json        文件名 / 尺寸 / 标题
"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

base = sys.argv[1].rstrip('/')


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


out = Path(opt('-o', 'assets/site'))
out.mkdir(parents=True, exist_ok=True)
vw = int(opt('--width', '1280'))
vh = int(opt('--height', '1000'))
paths = [p for p in opt('--paths', '/').split(',') if p]

# 没给 paths 就先打开首页抓内部链接
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome',
                          args=['--force-color-profile=srgb', '--hide-scrollbars',
                                '--font-render-hinting=none'])
    pg = b.new_page(viewport={'width': vw, 'height': vh}, device_scale_factor=2)

    if not paths:
        try:
            pg.goto(base + '/', wait_until='domcontentloaded', timeout=45000)
            pg.wait_for_timeout(2000)
            hrefs = pg.eval_on_selector_all(
                'a[href]',
                "els => els.map(e => e.getAttribute('href')).filter(Boolean)")
            keep = []
            for h in hrefs:
                if h.startswith('http') and not h.startswith(base):
                    continue
                if h.startswith('#') or h.startswith('mailto:'):
                    continue
                hp = h.replace(base, '') or '/'
                if hp not in keep:
                    keep.append(hp)
            paths = keep[:8] or ['/']
        except Exception as e:
            print('抓链接失败:', e)
            paths = ['/']

    print('要截的页面:', paths)
    meta = []
    for i, path in enumerate(paths):
        url = base + path if path.startswith('/') else base + '/' + path
        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=45000)
            pg.wait_for_timeout(1800)
            for sel in ('button:has-text("Accept")', '[aria-label="Close"]'):
                try:
                    pg.locator(sel).first.click(timeout=800)
                except Exception:
                    pass
            fn = f'page_{i:02d}.png'
            pg.screenshot(path=str(out / fn))
            meta.append({'file': fn, 'path': path, 'title': pg.title(),
                         'size': [vw * 2, vh * 2]})
            print(f'  {fn}  {path}  {pg.title()[:40]}')
        except Exception as e:
            print(f'  跳过 {path}: {str(e)[:80]}')
    b.close()

(out / 'index.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n{len(meta)} 张 → {out}')
print(f'每张 {vw*2}x{vh*2}，比例 {vw/vh:.2f}:1')
