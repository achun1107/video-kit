# -*- coding: utf-8 -*-
"""生成 GitHub Social Preview 图：assets/social-preview.png

规格 1280×640（2:1），GitHub Settings → Social preview 用的就是这个尺寸。

设计要点（社交卡片显示得很小，缩略图大概 300px 宽）：
  · 字必须大，120px 在缩略图里才剩 28px
  · 元素要少，超过 4 个就糊成一团
  · 对比要强，深底白字
"""
import contextlib
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
BG = '#0B0D11'
WHITE = '#FFFFFF'
MUTE = '#8A8F98'
ACCENT = '#E8613C'
ACCENT2 = '#2F9E8F'
GOLD = '#C9A227'

FONT_DIR = 'engine/fonts'


def font(size, bold=False):
    p = os.path.join(FONT_DIR, 'NotoSansSC-VF.ttf')
    if os.path.exists(p):
        f = ImageFont.truetype(p, size)
        with contextlib.suppress(Exception):
            f.set_variation_by_axes([700 if bold else 400])
        return f
    return ImageFont.load_default()


im = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(im)


def text(s, x, y, size=28, color=WHITE, anchor='la', bold=False):
    d.text((x, y), s, font=font(size, bold), fill=color, anchor=anchor)


# ── 背景：右上角一圈微光，避免大片死黑 ──
glow = Image.new('RGB', (W, H), BG)
gd = ImageDraw.Draw(glow)
for r in range(420, 0, -6):
    t = 1 - r / 420
    col = (
        int(11 + 40 * t * t),
        int(13 + 22 * t * t),
        int(17 + 46 * t * t),
    )
    gd.ellipse([W - 250 - r, -160 - r, W - 250 + r, -160 + r], fill=col)
im = Image.blend(im, glow, 0.85)
d = ImageDraw.Draw(im)

# ── 左：标题区 ──
LX = 90
text('video-kit', LX, 150, 128, WHITE, bold=True)

# 一句话
text('一条命令，把仓库变成竖屏视频', LX, 320, 44, '#D8DCE3')
text('GitHub 仓库 / 抖音链接  →  1080×1920 讲解片', LX, 386, 34, MUTE)

# 三个关键词，用小方块 + 文字
tags = [('纯函数渲染', ACCENT), ('零依赖', ACCENT2), ('两档文案', GOLD)]
tx = LX
for label, col in tags:
    font_t = font(26, True)
    tw = d.textlength(label, font=font_t)
    d.rounded_rectangle([tx, 470, tx + tw + 44, 526], 14, outline=col, width=2)
    text(label, tx + 22, 498, 26, col, anchor='lm', bold=True)
    tx += tw + 44 + 20

# ── 右：竖屏视频示意（三张卡的缩影）──
VX, VY = 880, 90
VW, VH = 300, 460
d.rounded_rectangle([VX - 4, VY - 4, VX + VW + 4, VY + VH + 4], 26, fill='#15191F', outline='#2A3038', width=2)

# 卡片 1：封面
d.rounded_rectangle([VX + 28, VY + 30, VX + VW - 28, VY + 170], 16, fill='#F4F1EC')
# 播放三角（不用 emoji —— NotoSansSC 没有 emoji 字形，会渲染成方块）
cx, cy, r = VX + VW / 2, VY + 76, 20
d.polygon([(cx - r * 0.55, cy - r), (cx - r * 0.55, cy + r), (cx + r * 0.9, cy)], fill='#23262B')
text('HyperFrames', VX + VW / 2, VY + 132, 24, '#23262B', anchor='mm', bold=True)

# 卡片 2：色块墙（5 个色块）
hues = ['#4A5D7E', '#C1432B', '#E8A0BF', '#7BA7BC', '#6B8E6B']
for i, hcol in enumerate(hues):
    bx = VX + 28 + i * 48
    d.rounded_rectangle([bx, VY + 200, bx + 40, VY + 240], 10, fill=hcol)

# 卡片 3：数字墙
text('80,464', VX + VW / 2, VY + 310, 52, ACCENT, anchor='mm', bold=True)
text('star', VX + VW / 2, VY + 358, 22, MUTE, anchor='mm')

# 卡片 4：字幕条
d.rounded_rectangle([VX + 28, VY + 392, VX + VW - 28, VY + 436], 12, fill='#20262E')
text('写 HTML，出视频', VX + VW / 2, VY + 414, 22, '#D8DCE3', anchor='mm')

# ── 页脚 ──
text('github.com/achun1107/video-kit', W / 2, H - 30, 22, '#4A5058', anchor='mm')

os.makedirs('assets', exist_ok=True)
out = 'assets/social-preview.png'
im.save(out, optimize=True)
size_kb = os.path.getsize(out) / 1024
print(f'{out}  {W}x{H}  {size_kb:.0f} KB')
