# -*- coding: utf-8 -*-
"""截 GitHub 仓库页面（给视频当素材）。

  python tools/shot-github.py <url> -o assets/repo.png                    # 整屏（默认）
  python tools/shot-github.py <url> -o assets/repo.png --mode head        # 只要仓库头
  python tools/shot-github.py <url> -o assets/repo.png --mode viewport    # 整屏

比例说明：视频卡片区宽 780。截 1280 宽 @2x = 2560 像素，
缩到 780 时有 3.3 倍余量 —— 局部放大后依然清晰。
"""
import contextlib
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

url = sys.argv[1]
def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

out = Path(opt("-o", "assets/repo.png"))
mode = opt("--mode", "viewport")
vw = int(opt("--width", "1280"))
vh = int(opt("--height", "1000"))

out.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome",
                          args=["--force-color-profile=srgb", "--hide-scrollbars",
                                "--font-render-hinting=none"])
    pg = b.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=2)
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(2800)
    for sel in ('button:has-text("Accept")', 'button:has-text("接受")', '[aria-label="Close"]'):
        with contextlib.suppress(Exception):
            pg.locator(sel).first.click(timeout=1200)
    pg.wait_for_timeout(600)

    if mode == "head":
        bb = None
        with contextlib.suppress(Exception):
            bb = pg.locator('#repository-container-header').first.bounding_box()
        clip = {"x": bb["x"], "y": bb["y"], "width": min(bb["width"], vw),
                "height": min(bb["height"] + 40, vh)} if bb else \
               {"x": 0, "y": 0, "width": vw, "height": 420}
        pg.screenshot(path=str(out), clip=clip)
    else:
        pg.screenshot(path=str(out))

    title = pg.title()
    star = ""
    star_focus = None
    name_focus = None
    for sel in ('#repo-stars-counter-star', 'a[href$="/stargazers"]'):
        try:
            loc = pg.locator(sel).first
            star = loc.inner_text(timeout=2000)
            if star:
                bb = loc.bounding_box()
                if bb:
                    star_focus = (bb["x"] + bb["width"] / 2,
                                  bb["y"] + bb["height"] / 2)
                break
        except Exception:
            pass
    # 仓库名（用于第二次聚焦）
    try:
        nb = pg.locator('h1 strong a, [itemprop="name"]').first.bounding_box()
        if nb:
            name_focus = (nb["x"] + nb["width"] / 2, nb["y"] + nb["height"] / 2)
    except Exception:
        pass
    b.close()

from PIL import Image

im = Image.open(out)
W, H = im.size
sx = im.size[0] / vw     # 截图相对 CSS 视口的缩放（device_scale_factor）
sy = im.size[1] / vh

def rel(pt):
    if not pt:
        return None
    return (round(pt[0] * sx / W, 4), round(pt[1] * sy / H, 4))

import json

meta = {
    "size": [W, H],
    "ratio": round(W / H, 4),
    "star_text": star,
    "star_at": rel(star_focus),
    "name_at": rel(name_focus),
}
Path(str(out) + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"saved {out}  {W}x{H}  ratio {W/H:.2f}:1")
print(f"title: {title}")
print(f"star : {star}")
print(f"meta : {out}.meta.json")
print(json.dumps(meta, ensure_ascii=False, indent=2))
print(f"display at width 780 -> 780x{round(780*H/W)}")

