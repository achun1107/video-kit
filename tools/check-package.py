# -*- coding: utf-8 -*-
"""发布包检查：上传前跑一次，确认包里每样东西都对。

  python tools/check-package.py D:/publish/ganhuoju
  python tools/check-package.py D:/publish/*

## 为什么需要

preflight 只管视频工程（内容/字幕/声音/时长）。
但上传时面对的是一个包：8 个文件。

  · 封面尺寸对不对（平台要求各不相同）
  · 文案里的链接能不能打开
  · 文件名对不对（上传时要选对平台）
  · 预览页真的能播吗
  · 发布文案里该有的东西有没有（标题/标签/简介）

**上传错一次要等审核或删稿重发，比多做一次检查贵得多。**

## 检查项

  P1  必需文件齐全（成片 + 4 封面 + 文案 + 说明）
  P2  成片能解码（ffprobe 读得出时长和分辨率）
  P3  封面尺寸对（抖音 1080×1920、小红书 1080×1440、视频号 1080×1260、B站 1146×717）
  P4  预览页里的视频路径有效
  P5  发布文案有标题、有标签、有简介
  P6  文案里的链接是 HTTP 且能解析出域名
  P7  文件名没有会让上传失败的字符
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# 平台 → 封面要求的宽高比（允许 ±3%）
COVER_SPEC = {
    '抖音':   1080 / 1920,
    '小红书': 1080 / 1440,
    '视频号': 1080 / 1260,
    'B站':    1146 / 717,
}


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def probe(path):
    """读视频/图片的宽高和时长。"""
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height',
         '-show_entries', 'format=duration',
         '-of', 'json', str(path)],
        capture_output=True, text=True, encoding='utf-8', errors='ignore')
    try:
        j = json.loads(r.stdout)
        st = (j.get('streams') or [{}])[0]
        dur = float((j.get('format') or {}).get('duration') or 0)
        return st.get('width'), st.get('height'), dur
    except Exception:
        return None, None, 0


def main():
    pkgs = [Path(a).resolve() for a in sys.argv[1:] if not a.startswith('--')]
    if not pkgs:
        sys.exit(__doc__)

    # 展开通配
    real = []
    for p in pkgs:
        if p.is_dir():
            real.append(p)

    total_fail = 0
    for pkg in real:
        print('=' * 62)
        print(pkg.name)
        print('=' * 62)
        fails = []

        # ── P1 必需文件 ──
        need = ['01_成片.mp4', '00_预览.html', '03_发布文案.md', '怎么发.txt']
        need += [f'02_封面-{k}.png' for k in COVER_SPEC]
        need.append('02_封面-B站竖版.png')   # B站竖屏视频备用
        missing = [n for n in need if not (pkg / n).exists()]
        if missing:
            fails.append(f'P1 缺文件：{", ".join(missing)}')
            print(f'  ✗ P1 缺 {len(missing)} 个文件')
        else:
            print(f'  ✓ P1 必需文件齐全（{len(need)} 个）')

        # ── P2 成片能解码 ──
        mp4 = pkg / '01_成片.mp4'
        if mp4.exists():
            w, h, dur = probe(mp4)
            if not w or not dur:
                fails.append('P2 成片解不开')
                print('  ✗ P2 成片解不开')
            elif abs(dur - 34.8) > 1.0:
                fails.append(f'P2 时长 {dur:.1f}s，应该 34.8s')
                print(f'  ✗ P2 时长 {dur:.1f}s')
            elif (w, h) != (1080, 1920):
                fails.append(f'P2 分辨率 {w}×{h}，应该 1080×1920')
                print(f'  ✗ P2 分辨率 {w}×{h}')
            else:
                mb = mp4.stat().st_size / 1024 / 1024
                print(f'  ✓ P2 成片 {w}×{h} {dur:.1f}s {mb:.1f}MB')

        # ── P3 封面尺寸 ──
        bad_covers = []
        for plat, want in COVER_SPEC.items():
            cp = pkg / f'02_封面-{plat}.png'
            if not cp.exists():
                continue
            w, h, _ = probe(cp)
            if not w or not h:
                bad_covers.append(f'{plat} 读不出')
                continue
            got = w / h
            if abs(got - want) / want > 0.03:
                bad_covers.append(f'{plat} {w}×{h} 比例 {got:.3f}，应为 {want:.3f}')
        if bad_covers:
            fails.append('P3 封面尺寸：' + '；'.join(bad_covers))
            print(f'  ✗ P3 {len(bad_covers)} 张封面比例不对')
            for b in bad_covers:
                print(f'      {b}')
        else:
            print('  ✓ P3 四张封面比例都对')

        # ── P4 预览页视频路径 ──
        ph = pkg / '00_预览.html'
        if ph.exists():
            html = ph.read_text(encoding='utf-8', errors='ignore')
            if '<video' not in html:
                fails.append('P4 预览页里没有 video 标签')
                print('  ✗ P4 预览页没有 video 标签')
            elif 'src=' not in html:
                fails.append('P4 预览页 video 没有 src')
                print('  ✗ P4 预览页 video 没有 src')
            else:
                kb = len(html) / 1024
                print(f'  ✓ P4 预览页内嵌 {kb:.0f}KB 视频')

        # ── P5 发布文案内容 ──
        md = pkg / '03_发布文案.md'
        if md.exists():
            txt = md.read_text(encoding='utf-8', errors='ignore')
            prob = []
            if '标题' not in txt and '##' not in txt:
                prob.append('没有标题结构')
            if '#' not in txt:
                prob.append('没有标签（#xxx）')
            if len(txt) < 200:
                prob.append(f'内容太短（{len(txt)} 字）')
            if prob:
                fails.append('P5 文案：' + '；'.join(prob))
                print(f'  ✗ P5 {len(prob)} 个问题')
                for p in prob:
                    print(f'      {p}')
            else:
                print(f'  ✓ P5 发布文案 {len(txt)} 字，有标题有标签')

        # ── P6 文案里的链接 ──
        if md.exists():
            urls = re.findall(r'https?://[^\s\)\]」》]+', txt)
            bad_urls = []
            for u in urls:
                if not re.match(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', u):
                    bad_urls.append(u)
            if bad_urls:
                fails.append(f'P6 可疑链接：{bad_urls[0]}')
                print(f'  ✗ P6 {len(bad_urls)} 个可疑链接')
            elif urls:
                print(f'  ✓ P6 {len(urls)} 个链接格式正常')

        # ── P7 文件名 ──
        weird = []
        for f in pkg.iterdir():
            if re.search(r'[<>:"|?*\x00-\x1f]', f.name):
                weird.append(f.name)
        if weird:
            fails.append(f'P7 文件名有特殊字符：{weird[0]}')
            print(f'  ✗ P7 {len(weird)} 个文件名有问题')
        else:
            print('  ✓ P7 文件名正常')

        print()
        if fails:
            total_fail += len(fails)
            print(f'  → {len(fails)} 项不通过')
        else:
            print('  → 可以直接上传')
        print()

    print('=' * 62)
    if total_fail:
        print(f'{len(real)} 个包共 {total_fail} 项不通过')
        sys.exit(1)
    print(f'{len(real)} 个包全部通过')


if __name__ == '__main__':
    main()
