#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""视觉回归测试：渲染固定 fixture 的几帧，和基准帧比对。

  python tests/vrt.py                  # 比对
  python tests/vrt.py --update         # 重建基准
  python tests/vrt.py --threshold 0.03 # 放宽容差
  python tests/vrt.py --keep           # 保留临时渲染产物

## 为什么基准帧不能当"绝对真值"

字体渲染跨平台不一致（Windows 用 GDI/DirectWrite，Linux 用 FreeType，
macOS 用 CoreText），同一份代码渲出来像素必有差异。
所以基准只能在**同一个环境**里当回归检测用：改完代码跑一次，
看画面有没有被意外改动。换机器要 `--update` 重建。

## 为什么不在 CI 里跑

真渲染要 Chrome + 43MB 字体 + 3-6 分钟。CI 里跑不起，
而且跨 runner 的字体差异会让比对一直红。CI 只跑结构检查。

## 比的是什么

不是逐像素相等（太脆），是**平均绝对误差 MAE**：
把两张图缩到 360×640 后逐像素求差的均值（0-255 区间归一化到 0-1）。
默认阈值 0.02（2%），差不多等于"看得出来的改动"。
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'tests' / 'fixture'
BASELINE = ROOT / 'tests' / 'baseline'
WORK = ROOT / 'tests' / '.vrt-work'

# 每张卡取一帧（避开切换点 ±0.1s）
# fixture 的卡片时间轴：c1 1.15 / c2 2.00 / c3 8.30 / c4 10.40 / c5 13.95 / c6 17.75 / c7 21.15
FRAMES = [
    ('card1_cover', 2.0),
    ('card2_stats', 5.0),
    ('card3_shot', 9.5),
    ('card4_features', 12.0),
    ('card5_highlight', 16.0),
    ('card6_list', 19.5),
    ('card7_conclusion', 24.0),
    ('subtitle', 6.5),      # 专门验字幕位置
    ('end', 30.0),          # 尾部
]

SCALE = (360, 640)          # 比对用尺寸，小一点免得基准太大


def run(cmd, cwd=None, quiet=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='ignore')
    if r.returncode != 0 and not quiet:
        print(r.stdout[-1500:] if r.stdout else '')
        print(r.stderr[-1500:] if r.stderr else '')
    return r


def prepare_work():
    """把 fixture 铺成一个能渲染的工程。"""
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    # 引擎和工具
    for rel in ['engine', 'tools']:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f'缺 {rel}/')
        shutil.copytree(src, WORK / rel,
                        ignore=shutil.ignore_patterns('fonts', '__pycache__'))

    # 字体：从仓库的 engine/fonts 复制（仓库里没有就报错，提示先跑 get_fonts）
    fonts_src = ROOT / 'engine' / 'fonts'
    if not fonts_src.exists() or not (fonts_src / 'NotoSansSC-VF.ttf').exists():
        raise SystemExit(
            '缺字体。先跑：python engine/get_fonts.py\n'
            '（视觉回归必须在有字体的环境下做，否则渲出来全是豆腐块）')
    shutil.copytree(fonts_src, WORK / 'engine' / 'fonts')

    # fixture 内容
    shutil.copy(FIXTURE / 'content.json', WORK / 'content.json')
    (WORK / 'audio').mkdir()
    (WORK / 'audio' / 'copy.json').write_text(
        (FIXTURE / 'copy.json').read_text(encoding='utf-8'), encoding='utf-8')

    # content.js
    d = json.loads((WORK / 'content.json').read_text(encoding='utf-8'))
    (WORK / 'content.js').write_text(
        'window.CONTENT = ' + json.dumps(d, ensure_ascii=False, indent=2) + ';\n',
        encoding='utf-8')

    # 字幕：手写，不跑 TTS（避免依赖网络和音频时长）
    subs = [
        {'a': 0.7, 'b': 3.0, 'zh': '这是一条用来做视觉回归测试的固定片子'},
        {'a': 3.0, 'b': 6.0, 'zh': '内容不变 画面也不该变'},
        {'a': 6.0, 'b': 9.0, 'zh': '改完代码跑一次比对'},
        {'a': 9.0, 'b': 12.0, 'zh': '就知道有没有碰坏别的卡片'},
        {'a': 12.0, 'b': 16.0, 'zh': '基准帧存在 tests/baseline 下'},
        {'a': 16.0, 'b': 20.0, 'zh': '比对时允许一点点像素差异'},
        {'a': 20.0, 'b': 26.0, 'zh': '字幕位置也是被比对的一部分'},
        {'a': 26.0, 'b': 30.0, 'zh': '完'},
    ]
    (WORK / 'audio' / 'subs.js').write_text(
        'window.SUBS = ' + json.dumps(subs, ensure_ascii=False, indent=2) + ';\n',
        encoding='utf-8')

    # index.html
    tpl = ROOT / 'tools' / 'index.template.html'
    shutil.copy(tpl, WORK / 'index.html')

    # film.js
    shutil.copy(ROOT / 'tools' / 'film-template.js', WORK / 'film.js')


def render_frames(times):
    """渲指定时间点的帧，返回 {name: path}。"""
    args = ['python', str(WORK / 'engine' / 'render.py'), str(WORK), '--stills']
    args += [str(t) for t in times]
    print(f'渲染 {len(times)} 帧 …')
    r = run(args)
    if r.returncode != 0:
        raise SystemExit('渲染失败')

    review = WORK / 'review'
    out = {}
    for name, t in FRAMES:
        # render.py 的命名是 s_00XX.XX.png
        p = review / f's_{t:05.2f}.png'
        if not p.exists():
            # 兼容其他命名
            cands = sorted(review.glob('s_*.png'))
            idx = [x[1] for x in FRAMES].index(t)
            p = cands[idx] if idx < len(cands) else None
        if p and p.exists():
            out[name] = p
    return out


def normalize(img):
    """缩到比对尺寸，转 RGB。"""
    return img.convert('RGB').resize(SCALE, Image.LANCZOS)


def mae(a, b):
    """平均绝对误差，归一化到 0-1。"""
    diff = ImageChops.difference(a, b)
    hist = diff.convert('L').histogram()
    total = sum(i * n for i, n in enumerate(hist))
    count = sum(hist)
    return (total / count) / 255.0 if count else 0.0


def save_diff(a, b, path):
    """生成差异图：变红的地方是改动处。"""
    diff = ImageChops.difference(a, b).convert('L')
    # 放大差异，让人眼能看见
    diff = diff.point(lambda x: min(255, x * 4))
    out = Image.merge('RGB', (diff, Image.new('L', diff.size, 0),
                              Image.new('L', diff.size, 0)))
    out.save(path, optimize=True)


def cmd_update():
    print('=== 重建基准 ===')
    prepare_work()
    frames = render_frames([t for _, t in FRAMES])
    if len(frames) != len(FRAMES):
        raise SystemExit(f'只渲出 {len(frames)}/{len(FRAMES)} 帧')

    BASELINE.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, p in frames.items():
        img = normalize(Image.open(p))
        dst = BASELINE / f'{name}.png'
        img.save(dst, optimize=True)
        sz = dst.stat().st_size
        total += sz
        print(f'  {name:20s} {sz/1024:6.1f} KB')

    meta = {
        'generated_at': subprocess.run(
            ['git', 'log', '-1', '--format=%H %ci'], cwd=ROOT,
            capture_output=True, text=True).stdout.strip(),
        'scale': list(SCALE),
        'frames': [n for n, _ in FRAMES],
        'times': [t for _, t in FRAMES],
        'note': '基准帧只在本机环境有效。换机器/换字体要 --update 重建。',
    }
    (BASELINE / 'manifest.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n合计 {total/1024:.0f} KB，写入 {BASELINE}')


def cmd_compare(threshold):
    if not BASELINE.exists():
        raise SystemExit('还没有基准帧，先跑：python tests/vrt.py --update')

    print(f'=== 比对（阈值 {threshold:.3f}）===')
    prepare_work()
    frames = render_frames([t for _, t in FRAMES])

    rows = []
    worst = (0.0, None)
    for name, _ in FRAMES:
        base_p = BASELINE / f'{name}.png'
        if not base_p.exists():
            rows.append((name, None, '基准缺失'))
            continue
        if name not in frames:
            rows.append((name, None, '渲染缺失'))
            continue

        a = normalize(Image.open(base_p))
        b = normalize(Image.open(frames[name]))
        d = mae(a, b)
        ok = d <= threshold
        rows.append((name, d, 'OK' if ok else 'CHANGED'))
        if d > worst[0]:
            worst = (d, name)
        if not ok:
            diff_dir = ROOT / 'tests' / '.vrt-diff'
            diff_dir.mkdir(exist_ok=True)
            save_diff(a, b, diff_dir / f'{name}-diff.png')

    print()
    for name, d, status in rows:
        if d is None:
            print(f'  ✗ {name:20s} {status}')
        else:
            bar = '█' * min(30, int(d / max(threshold, 1e-9) * 10))
            print(f'  {"✓" if status == "OK" else "✗"} {name:20s} MAE {d:.4f}  {bar}')

    bad = [r for r in rows if r[2] != 'OK']
    print()
    if bad:
        print(f'✗ {len(bad)} 帧超出阈值')
        if worst[1]:
            print(f'  最大差异：{worst[1]}  MAE {worst[0]:.4f}')
        print(f'  差异图：{ROOT / "tests" / ".vrt-diff"}')
        print()
        print('  如果改动是有意的：python tests/vrt.py --update')
        print('  如果是意外的：查 tools/film-template.js 或 engine/')
        return 1

    print(f'✓ 全部 {len(rows)} 帧在阈值内')
    return 0


def check_memory(min_gb=2.5):
    """渲染前预检可用内存。

    不预检的话，内存不够会卡在 window.READY，等 180 秒才超时，
    报错信息还看不出是内存的问题 —— 实际踩过：机器上开着 18 个
    浏览器标签，可用内存只剩 1.9 GB，渲染一直超时。
    """
    try:
        import psutil
        free = psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        # 没装 psutil 就跳过预检，用 ctypes 在 Windows 上兜一下
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            st = MEMORYSTATUSEX()
            st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
            free = st.ullAvailPhys / (1024 ** 3)
        except Exception:
            return True

    if free < min_gb:
        print(f'⚠ 可用内存只有 {free:.1f} GB，渲染至少要 {min_gb} GB')
        print('  Playwright 起 headless Chrome + 加载 43MB 字体，内存不够会卡在')
        print('  window.READY 上等 180 秒。关掉一些浏览器标签页再试。')
        return False
    print(f'  可用内存 {free:.1f} GB')
    return True


def main():
    threshold = 0.02
    if '--threshold' in sys.argv:
        threshold = float(sys.argv[sys.argv.index('--threshold') + 1])

    if '--skip-mem-check' not in sys.argv and not check_memory():
        return 2

    try:
        if '--update' in sys.argv:
            cmd_update()
            return 0
        return cmd_compare(threshold)
    finally:
        if '--keep' not in sys.argv and WORK.exists():
            shutil.rmtree(WORK, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
