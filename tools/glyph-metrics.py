# -*- coding: utf-8 -*-
"""量一帧底部区域的文字几何：亮像素的行分布与前 10 行的位置。

  python tools/glyph-metrics.py <图> [--region bottom]
"""
import sys
from PIL import Image
import numpy as np

path = sys.argv[1]
region = sys.argv[sys.argv.index('--region') + 1] if '--region' in sys.argv else 'bottom'

im = Image.open(path).convert('L')
W, H = im.size
bands = {'bottom': (int(H*0.75), H), 'title': (0, int(H*0.25)), 'full': (0, H)}
y0, y1 = bands[region]
a = np.asarray(im.crop((0, y0, W, y1)), dtype=np.float32) / 255.0
mask = a > 0.78

rows = mask.sum(axis=1)
cols = mask.sum(axis=0)
total = int(mask.sum())

# 找出有字的行区间（连续 > 3 像素）
active = rows > 3
if not active.any():
    print('该区域没有亮文字')
    sys.exit(0)

idx = np.where(active)[0]
# 连续段
segs, s = [], idx[0]
for i in range(1, len(idx)):
    if idx[i] != idx[i-1] + 1:
        segs.append((s, idx[i-1])); s = idx[i]
segs.append((s, idx[-1]))

print(f'图 {W}x{H}  区域 y={y0}-{y1}')
print(f'亮像素 {total} ({total/(W*(y1-y0))*100:.2f}% of region)')
print('文字行段（区域内坐标 → 全图坐标，高度）:')
for (a0, a1) in segs:
    print(f'  {a0:5d}-{a1:5d}  →  全图 {a0+y0:5d}-{a1+y0:5d}  高 {a1-a0+1}px')

cx = np.where(cols > 1)[0]
if len(cx):
    print(f'横向范围 {cx[0]}-{cx[-1]}（宽 {cx[-1]-cx[0]+1}px，画面宽 {W}）')
    print(f'文字高度 ≈ {max(b-a+1 for a,b in segs)}px')
