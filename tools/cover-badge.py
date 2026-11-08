# -*- coding: utf-8 -*-
"""封面加风格差异化。

## 问题

把四个封面缩到手机 feed 尺寸（250px 宽）并排看，
发现四个几乎一模一样 —— 只有背景圆环颜色微差。

观众刷到会以为是重复内容，平台也可能判相似封面。

## 改法

每套封面加一个风格角标（右上角小标签）+ 主色调微差：

  ajin      录屏讲解    蓝调
  ganhuoju  划重点      黄调
  xiaokai   一天一个    绿调
  weitu     刚开源      紫调

角标在 250px 缩略图下要能看清，所以字号不能太小（1080 宽下 32px）。
"""
import contextlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 风格 → (角标文字, 主色 RGB)
STYLES = {
    'ajin':     ('录屏讲解', (90, 160, 255)),
    'ganhuoju': ('划重点', (255, 200, 40)),
    'xiaokai':  ('一天一个', (120, 220, 130)),
    'weitu':    ('刚开源', (190, 150, 255)),
}


def font(size):
    root = Path(__file__).resolve().parent.parent
    p = root / 'engine' / 'fonts' / 'NotoSansSC-VF.ttf'
    if p.exists():
        f = ImageFont.truetype(str(p), size)
        with contextlib.suppress(Exception):
            f.set_variation_by_axes([700])
        return f
    return ImageFont.load_default()


def add_badge(path, text, color):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)

    size = int(W * 0.030)
    f = font(size)
    tw = d.textlength(text, font=f)
    pad_x, pad_y = int(W * 0.022), int(size * 0.55)
    bw, bh = int(tw + pad_x * 2), int(size + pad_y * 2)

    # 右上角，避开平台 UI（右侧 200px 内不放，但那是指竖屏底部区域）
    x1 = W - int(W * 0.055)
    y1 = int(H * 0.032)
    x0 = x1 - bw

    d.rounded_rectangle([x0, y1, x1, y1 + bh], radius=bh // 2,
                        fill=color + (0,), outline=color, width=2)
    # 半透明填充：直接画一层 overlay
    ov = Image.new('RGBA', (bw, bh), color + (150,))
    mask = Image.new('L', (bw, bh), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=255)
    im.paste(ov, (x0, y1), mask)

    d.text((x0 + bw / 2, y1 + bh / 2), text, font=f, fill='#FFFFFF', anchor='mm')
    im.save(path, optimize=True)
    return text


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for t, (text, color) in STYLES.items():
        if only and only != t:
            continue
        n = 0
        for plat in ['douyin', 'xhs', 'channels', 'bilibili']:
            p = Path(f'D:/publish/{t}/02_封面-{ {"douyin":"抖音","xhs":"小红书","channels":"视频号","bilibili":"B站"}[plat] }.png')
            if not p.exists():
                continue
            add_badge(p, text, color)
            n += 1
        print(f'  {t:10s} {text}  {n} 张')


if __name__ == '__main__':
    main()
