# -*- coding: utf-8 -*-
"""生成 README 用的流程图：assets/pipeline.png（布局修正版）

上一版输出框压在步骤上，这版改成：
  左：两个输入
  中：九步 2×5 网格
  下：输出横条
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1440, 820
BG = '#0B0D11'
INK = '#23262B'
MUTE = '#8A8F98'
ACCENT = '#E8613C'
ACCENT2 = '#2F9E8F'
GOLD = '#C9A227'
LINE = '#3A3F47'

FONT_DIR = 'engine/fonts'


def font(size, bold=False):
    p = os.path.join(FONT_DIR, 'NotoSansSC-VF.ttf')
    if os.path.exists(p):
        f = ImageFont.truetype(p, size)
        try:
            f.set_variation_by_axes([700 if bold else 400])
        except Exception:
            pass
        return f
    return ImageFont.load_default()


im = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(im)


def text(s, x, y, size=28, color=INK, anchor='la', bold=False):
    d.text((x, y), s, font=font(size, bold), fill=color, anchor=anchor)


def box(x, y, w, h, r=16, fill=None, outline=None, width=2):
    if fill:
        d.rounded_rectangle([x, y, x + w, y + h], r, fill=fill)
    if outline:
        d.rounded_rectangle([x, y, x + w, y + h], r, outline=outline, width=width)


def arrow(x1, y1, x2, y2, col=LINE, w=3):
    d.line([(x1, y1), (x2, y2)], fill=col, width=w)
    # 箭头头
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 12
    for s in (0.4, -0.4):
        d.line([(x2, y2), (x2 - L * math.cos(ang - s), y2 - L * math.sin(ang - s))],
               fill=col, width=w)


# ── 标题 ──
text('video-kit', 60, 40, 44, '#FFFFFF', bold=True)
text('一条命令：GitHub 仓库 / 抖音链接  →  竖屏讲解视频', 60, 100, 24, MUTE)

# ── 输入（左）──
ix, iy = 60, 190
box(ix, iy, 230, 96, 16, fill='#1A1E24', outline=ACCENT, width=2)
text('--repo', ix + 115, iy + 28, 24, ACCENT, anchor='ma', bold=True)
text('<url | 目录>', ix + 115, iy + 62, 18, '#D8DCE3', anchor='ma')

box(ix, iy + 116, 230, 96, 16, fill='#1A1E24', outline=ACCENT, width=2)
text('--douyin', ix + 115, iy + 144, 24, ACCENT, anchor='ma', bold=True)
text('<分享链接>', ix + 115, iy + 178, 18, '#D8DCE3', anchor='ma')

arrow(ix + 240, iy + 48, ix + 290, iy + 48)
arrow(ix + 240, iy + 164, ix + 290, iy + 164)

# ── 九步 2×5 ──
steps = [
    ('0', '铺骨架'), ('1', '仓库就位'), ('2', '抽内容'), ('3', '截图'), ('4', '配音'),
    ('5', '字幕'), ('6', '铺模板'), ('7', '渲染'), ('8', '混音'), ('9', '播放页'),
]
sx, sy = 360, 190
bw, bh, gx, gy = 176, 82, 16, 30
per_row = 5

for i, (no, name) in enumerate(steps):
    col = i % per_row
    row = i // per_row
    x = sx + col * (bw + gx)
    y = sy + row * (bh + gy)
    hot = i in (7, 8, 9)
    box(x, y, bw, bh, 14, fill='#FFE9E2' if hot else '#F4F1EC')
    text(no, x + 14, y + 10, 17, ACCENT, bold=True)
    text(name, x + bw / 2, y + bh / 2 + 6, 25, INK, anchor='mm', bold=True)
    if col < per_row - 1:
        d.line([(x + bw + 3, y + bh / 2), (x + bw + gx - 3, y + bh / 2)], fill=LINE, width=2)
    if col == per_row - 1 and i < len(steps) - 1:
        # 折行箭头：从行尾回到下一行行首
        x2 = sx
        y2 = y + bh + gy
        d.line([(x + bw / 2, y + bh + 3), (x + bw / 2, y + bh + gy / 2)], fill=LINE, width=2)
        d.line([(x + bw / 2, y + bh + gy / 2), (x2 + bw / 2, y + bh + gy / 2)], fill=LINE, width=2)
        arrow(x2 + bw / 2, y + bh + gy / 2, x2 + bw / 2, y2 - 3)

# ── 输出（下）──
oy = sy + 2 * bh + gy + 46
box(sx, oy, 1010, 96, 16, fill='#12201E', outline=ACCENT2, width=2)
text('输出', sx + 28, oy + 48, 24, ACCENT2, anchor='lm', bold=True)
d.line([(sx + 92, oy + 22), (sx + 92, oy + 74)], fill='#1F3B36', width=2)
outs = [('renders/final.mp4', 112), ('1080×1920 · 30fps', 350),
        ('中文人声 + 配乐', 610), ('renders/player.html', 830)]
for label, dx in outs:
    text(label, sx + dx, oy + 48, 19, '#D8DCE3', anchor='lm')

arrow(sx + 500, sy + 2 * bh + gy - 4, sx + 500, oy - 4, ACCENT2)

# ── 底部三特性 ──
fy = 620
feats = [
    ('纯函数渲染', ['每帧是 t 的函数', '任意 seek 可复现'], ACCENT),
    ('内容/画面分离', ['film.js 只读 content.json', '换仓库不用改代码'], ACCENT2),
    ('文案是人写的', ['其余全自动', '模板稿 + 参考稿两档'], GOLD),
]
for i, (t1, lines, col) in enumerate(feats):
    x = 60 + i * 450
    box(x, fy, 420, 120, 16, fill='#14181E', outline=col, width=2)
    text(t1, x + 24, fy + 20, 25, col, bold=True)
    for j, ln in enumerate(lines):
        text(ln, x + 24, fy + 60 + j * 26, 18, MUTE)

text('MIT  ·  github.com/achun1107/video-kit', W / 2, H - 28, 19, '#4A5058', anchor='mm')

os.makedirs('assets', exist_ok=True)
im.save('assets/pipeline.png', optimize=True)
print('assets/pipeline.png', im.size)
