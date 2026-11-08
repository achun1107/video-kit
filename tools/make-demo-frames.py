# -*- coding: utf-8 -*-
"""从成片抽 3 帧，拼成一张横向三联图：assets/demo-frames.png

抽帧要避开卡片切换点（切换前后 0.1s 是淡入淡出，抽到的是半透明过渡帧）。
hyperframes 那条片的切换点在 1.15 / 2.00 / 8.30 / 10.40 / 13.95 / 17.75 / 21.15，
所以取每张卡的中段：2.0（封面）、16.0（亮点数字）、24.0（结论）。

为什么不用 GIF：2MB+ 会拖慢 README 首屏，完整视频放 Release 附件。
"""
import contextlib
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

SRC = r'D:\DSH\achun\video-hyperframes\renders\final.mp4'
TIMES = [2.0, 16.0, 24.0]
CELL_W = 360
GAP = 24
PAD = 40
BG = '#0B0D11'

FONT_DIR = 'engine/fonts'


def font(size, bold=False):
    p = os.path.join(FONT_DIR, 'NotoSansSC-VF.ttf')
    if os.path.exists(p):
        f = ImageFont.truetype(p, size)
        with contextlib.suppress(Exception):
            f.set_variation_by_axes([700 if bold else 400])
        return f
    return ImageFont.load_default()


os.makedirs('_tmp_frames', exist_ok=True)
frames = []
for i, t in enumerate(TIMES):
    p = f'_tmp_frames/f{i}.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', SRC,
                    '-frames:v', '1', '-vf', f'scale={CELL_W}:-1', p], check=True)
    frames.append(Image.open(p))

cell_h = frames[0].height
HEAD_H = 96          # 标题区高度
LABEL_H = 34         # 标签行
FOOT_H = 52

W = PAD * 2 + CELL_W * 3 + GAP * 2
H = PAD + HEAD_H + LABEL_H + cell_h + FOOT_H

im = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(im)


def text(s, x, y, size=20, color='#8A8F98', anchor='la', bold=False):
    d.text((x, y), s, font=font(size, bold), fill=color, anchor=anchor)


# ── 顶部标题区 ──
text('一条命令的产物', PAD, PAD, 28, '#FFFFFF', bold=True)
text('1080 × 1920 · 30fps · 34.8s', W - PAD, PAD + 6, 18, '#4A5058', anchor='ra')

# ── 标签行 ──
labels = ['① 封面', '② 亮点', '③ 结论']
label_y = PAD + HEAD_H

# ── 三帧 ──
top = label_y + LABEL_H
for i, (img, label) in enumerate(zip(frames, labels, strict=False)):
    x = PAD + i * (CELL_W + GAP)
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width, img.height], 18, fill=255)
    im.paste(img, (x, top), mask)
    text(label, x + 4, label_y, 19, '#C9A227', bold=True)

# ── 底部 ──
text('完整成片见 Release 附件（demo.mp4）', W / 2, H - 28, 18, '#4A5058', anchor='mm')

os.makedirs('assets', exist_ok=True)
out = 'assets/demo-frames.png'
im.save(out, optimize=True)
print(f'{out}  {W}x{H}  {os.path.getsize(out)/1024:.0f} KB')

for i in range(len(TIMES)):
    with contextlib.suppress(Exception):
        os.remove(f'_tmp_frames/f{i}.png')
with contextlib.suppress(Exception):
    os.rmdir('_tmp_frames')
