# -*- coding: utf-8 -*-
"""手机尺寸预览：把成片缩到真实手机宽度，检查可读性。

  python tools/phone-preview.py <工程目录> [更多工程...]
  python tools/phone-preview.py D:/four/ganhuoju D:/four/weitu --time 9.5

## 为什么要这个

成片是 1080×1920，但用户是在手机上看的：
iPhone 14 逻辑宽度 390 CSS px，视频铺满屏宽。

1080 宽的 50px 字幕，缩到 390 宽只有 18px。
18px 的中文在手机上是能读的，但要确认不能更小。

## 用法

给每个工程抽一帧，缩到 390 宽，拼一张对比图。
自己看一眼就知道手机上能不能读。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

# 常见手机逻辑宽度
PHONES = [(375, 'SE'), (390, '14'), (430, 'ProMax')]


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def main():
    # 手动解析：跳过 --xxx 和它的值，剩下的才是工程目录
    args = []
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a.startswith('--'):
            i += 2      # 跳过参数名和它的值
        else:
            args.append(a)
            i += 1
    if not args:
        sys.exit(__doc__)
    t = float(arg('--time', '9.5'))
    out = Path(arg('--out', 'D:/phone-preview.png'))

    tmp = Path(tempfile.mkdtemp())
    frames = []
    for a in args:
        proj = Path(a).resolve()
        mp4 = proj / 'renders' / 'final.mp4'
        if not mp4.exists():
            print(f'跳过 {proj.name}（没有 final.mp4）')
            continue
        f = tmp / f'{proj.name}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t),
                        '-i', str(mp4), '-frames:v', '1', str(f)],
                       check=False)
        if f.exists():
            frames.append((proj.name, Image.open(f)))

    if not frames:
        sys.exit('没有可用的帧')

    # 统一缩到 iPhone 14 宽度（390）
    W = 390
    scaled = []
    for name, im in frames:
        h = int(im.height * W / im.width)
        scaled.append((name, im.resize((W, h), Image.LANCZOS)))

    gap = 14
    total_w = len(scaled) * W + (len(scaled) - 1) * gap
    total_h = max(i.height for _, i in scaled)
    canvas = Image.new('RGB', (total_w, total_h), '#141414')
    x = 0
    for _, im in scaled:
        canvas.paste(im, (x, 0))
        x += W + gap
    canvas.save(out)
    print(f'{out}  {total_w}×{total_h}')
    print(f'  模拟 iPhone 14 宽度 {W}px，帧位置 {t}s')
    print()
    print('  看什么：')
    print('    · 主标题能不能一眼读出来')
    print('    · 字幕字号够不够（中文 18px 是下限）')
    print('    · 截图里的细节看不清没关系，能认出是什么就行')


if __name__ == '__main__':
    main()
