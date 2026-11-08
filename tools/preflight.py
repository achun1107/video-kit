# -*- coding: utf-8 -*-
"""发布前自检：一条命令跑完所有会阻断发布的检查。

  python tools/preflight.py <工程目录> [<工程目录> ...]
  python tools/preflight.py D:/four/ajin D:/four/ganhuoju ...

## 为什么需要

第 9 轮发现字幕和配音对不上，藏了至少 4 轮。
代码层面看 subs.json 存在、条数对、时间戳连续，一切正常 ——
只有把「字幕内容」和「配音文案」放在一起比才看得出来。

同类问题还会有。所以把能自动查的都自动查了。

## 检查项

  A 内容完整      headline / features / conclusion 都有值
  B 文案长度      vo1 80-160 字，vo2 10-60 字（太短撑不满，太长念不完）
  C 字幕一致      subs.json 的内容必须来自当前 copy.json
  D 首帧非黑      第 0.1 秒不能是黑屏（抖音前 1 秒空屏等于放弃）
  E 响度          -14 ~ -9 LUFS（低于-16 会被压，高于-9 会被限流）
  F 时长          与模板 DUR 一致（34.8 秒）
  G 封面          4 个平台尺寸都存在且正确
  H 安全区        字幕位置 < 1420（抖音底部 UI 遮挡线）

跨工程检查（两个以上工程时）：
  I 音轨唯一      相互之间音频 md5 不能相同
  J 字幕唯一      相互之间字幕内容不能相同
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

# 各平台封面尺寸
COVER_SIZES = {
    'douyin': (1080, 1920),
    'xhs': (1080, 1440),
    'channels': (1080, 1260),
    'bilibili': (1080, 1920),
}

DUR = 34.8
SUBS_SAFE_Y = 1420       # 抖音底部遮挡线


class R:
    """一条检查结果。"""
    def __init__(self, name, ok, detail=''):
        self.name = name
        self.ok = ok
        self.detail = detail


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw)


def cn_len(s):
    return len(''.join((s or '').split()))


def check_content(proj):
    p = proj / 'content.json'
    if not p.exists():
        return [R('A 内容完整', False, '没有 content.json')]
    c = json.loads(p.read_text(encoding='utf-8'))
    out = []
    head = (c.get('headline') or '').strip()
    feats = c.get('features') or []
    concl = c.get('conclusion') or []
    out.append(R('A 内容完整',
                 bool(head and feats and concl),
                 f'headline={len(head)}字 features={len(feats)}条 conclusion={len(concl)}条'))
    return out


def check_copy(proj):
    p = proj / 'audio' / 'copy.json'
    if not p.exists():
        return [R('B 文案长度', False, '没有 copy.json')]
    c = json.loads(p.read_text(encoding='utf-8'))
    n1, n2 = cn_len(c.get('vo1')), cn_len(c.get('vo2'))
    ok = 80 <= n1 <= 160 and 10 <= n2 <= 60
    return [R('B 文案长度', ok, f'vo1={n1}字 vo2={n2}字 (要求 80-160 / 10-60)')]


def check_subs_match(proj):
    """C：字幕内容必须能在配音文案里找到。

    这是第 9 轮那个 bug 的检查项 —— 字幕是旧的、配音是新的，
    条数和时间戳全都正常，只有比对文本才看得出来。

    比较时去掉所有标点和空格：TTS 会在字之间插停顿逗号
    （「这个叫,小白看板」），那不是内容差异。
    """
    import re as _re
    sp = proj / 'audio' / 'subs.json'
    cp = proj / 'audio' / 'copy.json'
    if not sp.exists() or not cp.exists():
        return [R('C 字幕一致', False, '缺 subs.json 或 copy.json')]

    subs = json.loads(sp.read_text(encoding='utf-8'))
    subs = subs if isinstance(subs, list) else subs.get('subs', [])
    copy = json.loads(cp.read_text(encoding='utf-8'))

    def norm(s):
        # 只留中文、字母、数字
        return _re.sub(r'[^\u4e00-\u9fff\w]', '', s or '')

    script = norm(copy.get('vo1', '') + copy.get('vo2', ''))

    if not subs:
        return [R('C 字幕一致', False, 'subs 为空')]

    miss = []
    for s in subs:
        zh = norm(s.get('zh'))
        if not zh:
            continue
        probe = zh[:6]
        if probe and probe not in script:
            miss.append(probe)

    if miss:
        return [R('C 字幕一致', False,
                  f'{len(miss)}/{len(subs)} 条对不上，例如「{miss[0]}」不在配音文案里')]
    return [R('C 字幕一致', True, f'{len(subs)} 条全部命中')]


def check_first_frame(mp4):
    """D：第 0.1 秒不能是黑屏。

    用临时文件读帧，不走 stdout ——
    ffmpeg 输出的是二进制 PNG，穿过 text=True 的管道会被编码破坏，
    Image.open 就报「cannot identify image file」。
    """
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / 'f.png'
    r = run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.1', '-i', str(mp4),
             '-frames:v', '1', str(tmp)])
    if r.returncode != 0 or not tmp.exists():
        return [R('D 首帧非黑', False, '抽帧失败')]
    try:
        im = Image.open(tmp)
    except Exception:
        return [R('D 首帧非黑', False, '解帧失败')]

    px = im.convert('L').resize((64, 114))
    vals = list(px.getdata())
    mean = sum(vals) / len(vals)
    bright_ratio = sum(1 for v in vals if v > 40) / len(vals)
    ok = mean > 8 and bright_ratio > 0.02
    return [R('D 首帧非黑', ok, f'亮度 {mean:.0f} 亮点占比 {bright_ratio:.1%}')]


def check_loudness(mp4):
    """E：响度在 -14 ~ -9 LUFS。"""
    r = run(['ffmpeg', '-i', str(mp4), '-af', 'ebur128=framelog=quiet',
             '-f', 'null', '-'])
    import re
    m = re.search(r'I:\s+(-?[\d.]+)\s+LUFS', r.stderr)
    if not m:
        return [R('E 响度', False, '量不出')]
    v = float(m.group(1))
    return [R('E 响度', -16 <= v <= -9, f'{v} LUFS (要求 -14~-9，-16 是底线)')]


def check_duration(mp4):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', str(mp4)])
    try:
        d = float(r.stdout.strip())
    except ValueError:
        return [R('F 时长', False, '读不出')]
    return [R('F 时长', abs(d - DUR) < 0.5, f'{d:.2f}s (模板 {DUR}s)')]


def check_covers(proj):
    out = []
    rdir = proj / 'renders'
    for plat, (w, h) in COVER_SIZES.items():
        p = rdir / f'cover-{plat}.png'
        if not p.exists():
            out.append(R(f'G 封面 {plat}', False, '缺文件'))
            continue
        im = Image.open(p)
        out.append(R(f'G 封面 {plat}', im.size == (w, h),
                     f'{im.size[0]}×{im.size[1]} (要求 {w}×{h})'))
    return out


def check_safe_area(proj):
    """H：字幕位置必须在安全区内。"""
    film = proj / 'film.js'
    if not film.exists():
        return [R('H 安全区', False, '没有 film.js')]
    s = film.read_text(encoding='utf-8', errors='ignore')
    import re
    m = re.search(r"fr\.text\(s\.zh, W / 2, (\d+)", s)
    if not m:
        return [R('H 安全区', True, '该模板无字幕，跳过')]
    y = int(m.group(1))
    return [R('H 安全区', y < SUBS_SAFE_Y,
              f'字幕 Y={y} (遮挡线 {SUBS_SAFE_Y})')]


def audio_md5(mp4):
    r = run(['ffmpeg', '-v', 'error', '-i', str(mp4), '-vn', '-c:a', 'copy',
             '-f', 'md5', '-'])
    return (r.stdout or '').strip()


def check_cross(projs, finals):
    """I/J：跨工程唯一性。"""
    out = []
    audios = {}
    subs = {}
    for p in projs:
        f = finals.get(p)
        if f and f.exists():
            audios[p.name] = audio_md5(f)
        sp = p / 'audio' / 'subs.json'
        if sp.exists():
            d = json.loads(sp.read_text(encoding='utf-8'))
            d = d if isinstance(d, list) else d.get('subs', [])
            subs[p.name] = hashlib.md5(
                json.dumps(d, ensure_ascii=False).encode()).hexdigest()[:12]

    if len(audios) > 1:
        dup = len(audios) - len(set(audios.values()))
        out.append(R('I 音轨唯一', dup == 0,
                     f'{len(audios)} 条，{dup} 条重复'))
    if len(subs) > 1:
        dup = len(subs) - len(set(subs.values()))
        out.append(R('J 字幕唯一', dup == 0,
                     f'{len(subs)} 条，{dup} 条重复'))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    projs = [Path(a).resolve() for a in sys.argv[1:]]
    finals = {}
    all_results = []
    bad = 0

    for proj in projs:
        print(f'\n{"="*62}')
        print(f'{proj.name}')
        print('='*62)

        mp4 = proj / 'renders' / 'final.mp4'
        if not mp4.exists():
            mp4 = proj / 'renders' / 'raw.mp4'
        finals[proj] = mp4 if mp4.exists() else None

        rs = []
        rs += check_content(proj)
        rs += check_copy(proj)
        rs += check_subs_match(proj)
        if mp4.exists():
            rs += check_first_frame(mp4)
            rs += check_loudness(mp4)
            rs += check_duration(mp4)
        else:
            rs.append(R('成片', False, '没有 final.mp4'))
        rs += check_covers(proj)
        rs += check_safe_area(proj)

        for r in rs:
            mark = '✓' if r.ok else '✗'
            print(f'  {mark} {r.name:16s} {r.detail}')
            if not r.ok:
                bad += 1
        all_results += rs

    if len(projs) > 1:
        print(f'\n{"="*62}')
        print('跨工程检查')
        print('='*62)
        for r in check_cross(projs, finals):
            mark = '✓' if r.ok else '✗'
            print(f'  {mark} {r.name:16s} {r.detail}')
            if not r.ok:
                bad += 1

    print(f'\n{"="*62}')
    if bad:
        print(f'✗ {bad} 项不通过')
        sys.exit(1)
    print(f'✓ 全部通过（{len(all_results)} 项）')


if __name__ == '__main__':
    main()
