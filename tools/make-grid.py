# -*- coding: utf-8 -*-
"""把目录里的帧拼成一张网格图，给视觉分析用。

  python tools/make-grid.py <帧目录> -o grid.jpg --cols 4 --cell 320
  python tools/make-grid.py <视频文件> -o grid.jpg --every 3 --cols 4

两种模式：
  目录   把已有帧拼起来
  视频   按固定间隔抽帧再拼
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def font(size):
    for p in ('engine/fonts/NotoSansSC-VF.ttf',
              str(Path(__file__).resolve().parent.parent / 'engine/fonts/NotoSansSC-VF.ttf')):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    out = arg('-o', 'grid.jpg')
    cols = int(arg('--cols', '4'))
    cell = int(arg('--cell', '320'))
    every = float(arg('--every', '3'))

    frames = []

    if src.is_dir():
        for p in sorted(src.glob('*.png')):
            frames.append((p.name, Image.open(p)))
    else:
        # 从视频抽帧
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                            'format=duration', '-of', 'default=nw=1:nk=1', str(src)],
                           capture_output=True, text=True)
        try:
            dur = float(r.stdout.strip())
        except ValueError:
            dur = 30
        tmp = Path(tempfile.mkdtemp())
        times = []
        t = 0.0
        while t < dur:
            times.append(round(t, 1))
            t += every
        for i, t in enumerate(times):
            p = tmp / f'{i:03d}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t),
                            '-i', str(src), '-frames:v', '1',
                            '-vf', f'scale={cell}:-1', str(p)], check=False)
            if p.exists():
                frames.append((f'{t:.1f}s', Image.open(p)))

    if not frames:
        sys.exit('没有帧')

    # 统一尺寸
    w, h = frames[0][1].size
    frames = [(n, im.resize((w, h))) for n, im in frames]

    rows = (len(frames) + cols - 1) // cols
    PAD = 6
    LABEL = 26
    W = cols * w + (cols + 1) * PAD
    H = rows * (h + LABEL) + (rows + 1) * PAD

    im = Image.new('RGB', (W, H), '#101010')
    d = ImageDraw.Draw(im)
    f = font(16)

    for i, (name, frame) in enumerate(frames):
        c, r = i % cols, i // cols
        x = PAD + c * (w + PAD)
        y = PAD + r * (h + LABEL + PAD)
        im.paste(frame, (x, y))
        d.text((x + 4, y + h + 4), name, font=f, fill='#CCCCCC')

    im.save(out, quality=88)
    print(f'{out}  {len(frames)} 帧 {cols}列  {W}x{H}')


if __name__ == '__main__':
    main()
