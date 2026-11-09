# -*- coding: utf-8 -*-
"""量化检查：画面里的文字在手机上够不够大。

  python tools/check-text-size.py D:/four/ganhuoju

## 为什么需要

phone-preview 靠肉眼看，没有判据。但这是最影响观感的一件事：
1080 宽的字幕，在 iPhone 上只有 390 CSS px 宽显示，缩到 36%。

1080 下 44px 的字，到手机上只有 16px。中文 16px 是下限。

## 怎么量

不读模板源码（变量太多，容易读错），直接从渲染帧上量：

1. 取字幕区域（Y 1280~1400，避开 CTA 和内容）
2. 找该区域内亮像素的包围盒高度 = 实际字高
3. 换算：手机像素 = 字高 × (390 / 1080)
4. 和下限比

## 判据（中文，iPhone 390 逻辑宽度）

  字幕/正文    >= 15px  小于这个手机上要凑近看
  重要数字      >= 22px
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

PHONE_W = 390      # iPhone 14 逻辑宽度
CANVAS_W = 1080
SCALE = PHONE_W / CANVAS_W

# 字幕区（避开 CTA 的渐变黑带和下方 UI 区）
SUB_Y0, SUB_Y1 = 1270, 1400


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def text_height(img, y0, y1, thr=150):
    """在指定纵向区间里，找亮像素的包围盒高度。"""
    w, h = img.size
    crop = img.crop((0, y0, w, min(y1, h))).convert('L')

    # 按行统计亮像素数
    px = crop.load()
    cw, ch = crop.size
    rows = []
    for y in range(ch):
        n = 0
        for x in range(0, cw, 2):        # 隔列采样，够用且快
            if px[x, y] > thr:
                n += 1
        rows.append(n)

    # 有字的行：亮像素数超过宽度 0.5%
    on = [i for i, n in enumerate(rows) if n > cw * 0.005]
    if not on:
        return 0
    # 取最长连续段
    best = cur = 1
    for i in range(1, len(on)):
        if on[i] - on[i - 1] <= 2:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return on[-1] - on[0] + 1 if len(on) > 2 else 0


def main():
    projs = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not projs:
        sys.exit(__doc__)

    min_sub = float(arg('--min', '15'))
    tmp = Path(tempfile.mkdtemp())

    print(f'手机宽度 {PHONE_W}px（缩放 {SCALE:.3f}），字幕区 Y {SUB_Y0}-{SUB_Y1}')
    print(f'{"工程":14s} {"样本":>4s} {"字高(1080)":>11s} {"手机px":>8s}  判断')
    print('-' * 62)

    for p in projs:
        proj = Path(p).resolve()
        mp4 = proj / 'renders' / 'final.mp4'
        if not mp4.exists():
            print(f'{proj.name:14s} 没有 final.mp4')
            continue

        # 抽 8 帧（避开开场 3 秒和结尾 3 秒）
        times = [6 + i * 3.2 for i in range(8)]
        heights = []
        for i, t in enumerate(times):
            f = tmp / f'{proj.name}-{i}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t),
                            '-i', str(mp4), '-frames:v', '1', str(f)], check=False)
            if not f.exists():
                continue
            hh = text_height(Image.open(f), SUB_Y0, SUB_Y1)
            if hh > 4:
                heights.append(hh)

        if not heights:
            print(f'{proj.name:14s} 抽不到字幕')
            continue

        heights.sort()
        med = heights[len(heights) // 2]
        phone = med * SCALE

        if phone >= min_sub + 3:
            verdict = '✓ 够大'
        elif phone >= min_sub:
            verdict = '△ 刚好'
        else:
            verdict = f'✗ 太小（下限 {min_sub}px）'

        print(f'{proj.name:14s} {len(heights):4d} {med:9d}px {phone:7.1f}px  {verdict}')


if __name__ == '__main__':
    main()
