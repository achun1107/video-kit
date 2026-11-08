# -*- coding: utf-8 -*-
"""生成发布用封面 —— 重新设计，不抽视频帧。

## 为什么不用抽帧

第一版抽第 3 秒的帧，结果图上出现了两套标题：
抽的那一帧本身就有"小白看板 / 让 Agent 帮你写代码"，
我又叠了一层上去，白字黄字打架。

抽帧的方案从根上就有问题：视频里每个位置都有字。

## 现在的做法

用 content.json + 干净的 GitHub 截图（assets/repo.png）重新排版：

  ┌──────────────────┐
  │  ● 开源项目       │  小标签
  │                  │
  │    小白看板       │  大标题（自适应字号）
  │  让 Agent 帮你写代码 │  副标题
  │                  │
  │   [GitHub 截图]   │  截图卡片
  │                  │
  │   130 ★ 完全开源   │  数据条
  └──────────────────┘

各平台尺寸：
  抖音     1080×1920
  小红书   1080×1440（主feed是 3:4）
  视频号   1080×1260（6:7）
  B站竖屏  1080×1920

  python tools/make-cover.py <工程目录>
"""
import contextlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def font(size, bold=True, hand=False):
    root = Path(__file__).resolve().parent.parent
    name = 'MaShanZheng-Regular.ttf' if hand else 'NotoSansSC-VF.ttf'
    p = root / 'engine' / 'fonts' / name
    if p.exists():
        f = ImageFont.truetype(str(p), size)
        if bold and not hand:
            # 可变字体设字重；有些字重轴不支持就跳过，不报错
            with contextlib.suppress(Exception):
                f.set_variation_by_axes([700])
        return f
    return ImageFont.load_default()


def fit_font(draw, texts, max_w, start, hand=False, floor=36):
    """字号从 start 往下试，直到最宽那行不超过 max_w。"""
    size = start
    while size > floor:
        f = font(size, hand=hand)
        widest = max(draw.textlength(t, font=f) for t in texts) if texts else 0
        if widest <= max_w:
            return f, size
        size = int(size * 0.93)
    return font(floor, hand=hand), floor


def make_cover(size, out, c, shot_path, accent='#FFE500'):
    W, H = size
    im = Image.new('RGB', (W, H), '#0B0D11')
    d = ImageDraw.Draw(im)

    # ── 背景：径向光晕（模拟参考视频的深色科技感）──
    # 同心圆光晕：40 圈，对比度压低（第一版 60 圈像靶心，抢标题）
    for i in range(40, 0, -1):
        r = int(W * (0.12 + i * 0.009))
        a = int(4 + i * 0.28)
        d.ellipse([W // 2 - r, int(H * 0.28) - r, W // 2 + r, int(H * 0.28) + r],
                  fill=None, outline=(18 + a, 34 + a, 52 + a), width=1)

    name = c.get('namePlain') or c.get('name') or '项目'
    head = (c.get('headline') or '').strip()
    stats = c.get('stats') or {}
    star = stats.get('star')

    # ── 顶部小标签 ──
    f_tag = font(int(W * 0.024), bold=False)
    tag = 'GitHub 开源项目'
    tw = d.textlength(tag, font=f_tag)
    tx, ty = int(W * 0.06), int(H * 0.045)
    d.rounded_rectangle([tx - 14, ty - 10, tx + tw + 14, ty + 34],
                        radius=22, fill='#161B22', outline='#2A3341', width=1)
    d.text((tx + tw / 2, ty + 11), tag, font=f_tag, fill='#8B98A8', anchor='mm')

    # ── 主标题（项目名，最多 6 字）──
    title = name[:6]
    y_title = int(H * 0.115)
    f_t, s_t = fit_font(d, [title], W * 0.84, int(W * 0.115), hand=True, floor=48)
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
        d.text((W // 2 + dx, y_title + dy), title, font=f_t, fill='#000000', anchor='ma')
    d.text((W // 2, y_title), title, font=f_t, fill='#FFFFFF', anchor='ma')

    # ── 副标题（一句话卖点）──
    if head:
        sub = head[:18]
        y_sub = y_title + int(s_t * 1.12)
        f_s, _ = fit_font(d, [sub], W * 0.86, int(W * 0.042), hand=False, floor=22)
        d.text((W // 2, y_sub), sub, font=f_s, fill='#9FB0C4', anchor='ma')

    # ── 截图卡片 ──
    if shot_path and Path(shot_path).exists():
        shot = Image.open(shot_path).convert('RGB')
        cw = int(W * 0.84)
        ch = int(cw * shot.height / shot.width)
        max_ch = int(H * 0.38)   # 再压一点，给底部数据条腾地方
        if ch > max_ch:
            ch = max_ch
            cw = int(ch * shot.width / shot.height)
        shot = shot.resize((cw, ch), Image.LANCZOS)
        sx, sy = (W - cw) // 2, int(H * 0.40)
        # 边框
        d.rounded_rectangle([sx - 4, sy - 4, sx + cw + 4, sy + ch + 4],
                            radius=10, fill='#2A3341')
        im.paste(shot, (sx, sy))
        shot_bottom = sy + ch
    else:
        shot_bottom = int(H * 0.40)

    # ── 底部数据条 ──
    # 必须落在截图下方，不能压图（第一版 min() 会取到 0.80H，正好压在截图底部）
    y_data = shot_bottom + int(H * 0.055)
    y_limit = int(H * 0.86)   # 留 14% 给平台 UI
    if y_data > y_limit:
        y_data = y_limit
    parts = []
    if star:
        parts.append(f'{star:,} ★')
    parts.append('完全开源')

    line = '   ·   '.join(parts)
    f_d, _ = fit_font(d, [line], W * 0.80, int(W * 0.058), hand=False, floor=24)

    # 数据条底色
    lw = d.textlength(line, font=f_d)
    d.rounded_rectangle([W // 2 - lw / 2 - 26, y_data - 30,
                         W // 2 + lw / 2 + 26, y_data + 42],
                        radius=16, fill='#1A2230')
    d.text((W // 2, y_data + 5), line, font=f_d, fill=accent, anchor='mm')

    # ── 底部留白标记（给平台 UI）──
    # 抖音底部 480px、小红书 360px、视频号 300px，取 0.22H 做下限
    # （这里不画东西，只是提醒设计时别往下放内容）

    im.save(out, optimize=True)
    return out


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    cp = proj / 'content.json'
    if not cp.exists():
        sys.exit(f'没有 {cp}')
    c = json.loads(cp.read_text(encoding='utf-8'))

    # star 从 API 补 —— extract-content 只读本地文件，拿不到 API 数据
    stats = c.get('stats') or {}
    if not stats.get('star'):
        repo_full = c.get('repo') or ''
        owner = c.get('owner') or ''
        if owner and repo_full:
            full = f'{owner}/{repo_full}'
            try:
                import os
                import urllib.request
                req = urllib.request.Request(
                    f'https://api.github.com/repos/{full}',
                    headers={'User-Agent': 'video-kit',
                             **({'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}'}
                                if os.environ.get('GITHUB_TOKEN') else {})})
                with urllib.request.urlopen(req, timeout=15) as r:
                    j = json.loads(r.read().decode())
                stats['star'] = j.get('stargazers_count')
                c['stats'] = stats
                print(f'  star 从 API 补到：{stats["star"]:,}')
            except Exception as e:
                print(f'  star 补全失败（{type(e).__name__}），封面不显示数字')

    shot = proj / 'assets' / 'repo.png'
    if not shot.exists():
        shot = None

    # 小红书主feed露出的少，用更方一点的尺寸
    sizes = {
        'douyin':   (1080, 1920),
        'xhs':      (1080, 1440),
        'channels': (1080, 1260),
        'bilibili': (1080, 1920),
    }

    outdir = proj / 'renders'
    outdir.mkdir(exist_ok=True)

    print(f'  {c.get("namePlain") or c.get("name")}')
    for plat, size in sizes.items():
        p = outdir / f'cover-{plat}.png'
        make_cover(size, p, c, shot)
        print(f'  {plat:10s} {size[0]}×{size[1]}  {p.name}  '
              f'{p.stat().st_size // 1024}KB')

    print(f'\n在 {outdir}')


if __name__ == '__main__':
    main()
