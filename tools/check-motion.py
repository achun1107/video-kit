# -*- coding: utf-8 -*-
"""量四条片子前 2 秒的画面变化量。

  python tools/check-motion.py D:/four/ganhuoju D:/four/ajin ...

## 为什么

第 32 轮发现 ganhuoju 前 3.6 秒画面几乎静止（相邻帧差异 1~4%），
在抖音上等于劝人划走。加了入场动画后提到 7~26%。

其他三条有没有同样的问题？用同一把尺子量一遍。

## 判据

抖音上前 2 秒要有明显变化。参考值：
  > 8%   合格（有明显动作）
  3-8%   偏静（只有缓慢推拉）
  < 3%   危险（几乎静止）
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

# 采样点：0.05 / 0.4 / 0.8 / 1.3 / 2.0
TIMES = [0.05, 0.4, 0.8, 1.3, 2.0]


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def grab(mp4, t, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t),
                    '-i', str(mp4), '-frames:v', '1', str(out)], check=False)
    return out.exists()


def main():
    pkgs = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not pkgs:
        sys.exit(__doc__)

    tmp = Path(tempfile.mkdtemp())
    print(f'{"工程":22s} {"0→0.4s":>9s} {"0.4→0.8":>9s} {"0.8→1.3":>9s} {"1.3→2.0":>9s}  判断')
    print('-' * 82)

    for p in pkgs:
        proj = Path(p).resolve()
        mp4 = proj / 'renders' / 'final.mp4'
        if not mp4.exists():
            print(f'{proj.name:22s} 没有 final.mp4')
            continue

        imgs = []
        for t in TIMES:
            f = tmp / f'{proj.name}-{t}.png'
            if grab(mp4, t, f):
                imgs.append((t, Image.open(f).convert('L').resize((216, 384))))

        if len(imgs) < 2:
            print(f'{proj.name:22s} 抽帧失败')
            continue

        diffs = []
        for i in range(1, len(imgs)):
            d = ImageChops.difference(imgs[i - 1][1], imgs[i][1])
            changed = sum(1 for px in d.getdata() if px > 8) / (216 * 384)
            diffs.append(changed * 100)

        # 前两秒的平均变化
        avg = sum(diffs) / len(diffs)
        if avg >= 8:
            verdict = '合格'
        elif avg >= 3:
            verdict = '偏静'
        else:
            verdict = '★危险·几乎静止★'

        cells = '  '.join(f'{d:7.1f}%' for d in diffs)
        print(f'{proj.name:22s} {cells}  {verdict}')


if __name__ == '__main__':
    main()
