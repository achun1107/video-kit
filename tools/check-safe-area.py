# -*- coding: utf-8 -*-
"""横向安全区检查：字幕会不会伸进平台右侧 UI 区。

  python tools/check-safe-area.py D:/four/ganhuoju

## 为什么改成计算，不再测像素

前两版都是"从渲染帧上找白色像素的包围盒"，两次都失败：

  · 第一版把字幕上方的内容框进去了（量到字高 107px，但字号只有 60）
  · 第二版把画面 grain 噪点当成文字了（阈值提到 210 还是误报 1079px）

像素法在这个场景不可靠：画面里有截图、渐变、颗粒噪点，
很难只框住字幕。

## 改成算

字幕宽度可以直接算出来，不需要看画面：

  显示宽度 vw × 字号 size = 文字宽度（中文 1 字 = 1 个显示宽度）
  居中后左边界 = 540 - 宽/2，右边界 = 540 + 宽/2

字号公式在模板里是固定的：size = min(56, round(900 / vw))

所以从 subs.json 读每条的 vw，就能算出右边界，稳。

## 判据

抖音右侧 UI 约 200px（1080 宽下），右边界必须 ≤ 880。
"""
import json
import sys
from pathlib import Path

W = 1080
RIGHT_LIMIT = W - 200      # 880

SIZE_CAP = 56
SIZE_BASE = 640


def display_width(text):
    """中文/全角算 1，ASCII 算 0.56，空格 0.3。"""
    n = 0.0
    for ch in text:
        o = ord(ch)
        if o < 128:
            n += 0.3 if ch == ' ' else 0.56
        else:
            n += 1.0
    return n


def main():
    projs = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not projs:
        sys.exit(__doc__)

    print(f'右侧 UI 区从 x={RIGHT_LIMIT} 起（宽 200px）')
    print(f'字号 = min({SIZE_CAP}, round({SIZE_BASE} / 字宽))')
    print()
    print(f'{"工程":14s} {"条数":>4s} {"最大字宽":>9s} {"字号":>6s} {"右边界":>8s} {"余量":>7s}  判断')
    print('-' * 74)

    bad = 0
    for p in projs:
        proj = Path(p).resolve()
        sp = proj / 'audio' / 'subs.json'
        if not sp.exists():
            print(f'{proj.name:14s} 没有 subs.json')
            continue

        subs = json.loads(open(sp, encoding='utf-8').read())
        subs = subs if isinstance(subs, list) else subs.get('subs', [])
        if not subs:
            print(f'{proj.name:14s} 没有字幕')
            continue

        worst = (0, 0, 0)   # (vw, size, right)
        for s in subs:
            vw = display_width(s.get('zh', ''))
            size = min(SIZE_CAP, round(SIZE_BASE / max(vw, 1)))
            right = W / 2 + vw * size / 2
            if right > worst[2]:
                worst = (vw, size, right)

        vw, size, right = worst
        margin = RIGHT_LIMIT - right
        if margin >= 20:
            verdict = '✓ 安全'
        elif margin >= 0:
            verdict = '△ 贴边'
        else:
            verdict = f'✗ 侵入 {-margin:.0f}px'
            bad += 1

        print(f'{proj.name:14s} {len(subs):4d} {vw:9.1f} {size:5d}px '
              f'{right:7.0f}px {margin:+6.0f}px  {verdict}')

    print()
    if bad:
        print(f'{bad} 个工程会侵入右侧 UI 区')
        sys.exit(1)
    print('全部安全')


if __name__ == '__main__':
    main()
