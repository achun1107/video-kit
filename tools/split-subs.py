# -*- coding: utf-8 -*-
"""把长字幕拆成短视频节奏的短句。

  python tools/split-subs.py <工程目录>
  python tools/split-subs.py D:/four/ganhuoju --max 12

## 为什么

跑 preflight 之外单独查了一下字幕长度：

  ajin      第 3 条 49 字 / 停留 7.7 秒
  ganhuoju  第 3 条 46 字 / 停留 8.1 秒

一条字幕停 8 秒，是 YouTube 口播的做法。抖音观众 2 秒没变化就划走了。

抖音的标准：
  · 每条字幕 8~14 字
  · 每 1.5~2.5 秒换一次

而且 49 字在 1080 宽屏上，字号缩到 30px 也占 1470px，放不下。

## 怎么拆

1. 按标点切（、，。；：！？）
2. 相邻短句合并到 max 字以内
3. 时间按字数比例分配（总时长不变，配音对得上）

## 注意

只拆 subs.json / subs.js，不动配音。
所以时间轴必须严格按字数比例分配 —— 拆完还是和原来的 TTS 时间戳对齐。
"""
import json
import re
import sys
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def cn_len(s):
    """按实际显示宽度算：中文 1，英文/数字 0.55，空格 0.3。"""
    n = 0.0
    for ch in s:
        if '\u4e00' <= ch <= '\u9fff':
            n += 1
        elif ch == ' ':
            n += 0.3
        else:
            n += 0.55
    return n


def split_one(text, max_len):
    """把一条长字幕拆成若干短句。"""
    # 先按标点切，保留标点
    parts = re.split(r'(?<=[，。、；：！？,.;:!?])', text)
    parts = [p for p in parts if p.strip()]
    if not parts:
        return [text]

    out = []
    cur = ''
    for p in parts:
        if not cur:
            cur = p
        elif cn_len(cur + p) <= max_len:
            cur += p
        else:
            out.append(cur)
            cur = p
    if cur:
        out.append(cur)

    # 还有超长的，硬切
    final = []
    for s in out:
        if cn_len(s) <= max_len * 1.35:
            final.append(s)
            continue
        # 按字符数硬切
        chars = list(s)
        chunk = ''
        for ch in chars:
            if cn_len(chunk + ch) > max_len:
                final.append(chunk)
                chunk = ch
            else:
                chunk += ch
        if chunk:
            final.append(chunk)

    return final if final else [text]


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    max_len = float(arg('--max', '12'))

    sp = proj / 'audio' / 'subs.json'
    if not sp.exists():
        sys.exit(f'没有 {sp}')
    raw = json.loads(sp.read_text(encoding='utf-8'))
    subs = raw if isinstance(raw, list) else raw.get('subs', [])
    if not subs:
        sys.exit('subs 为空')

    before = [(s['a'], s['b'], s.get('zh', '')) for s in subs]

    out = []
    for s in subs:
        a, b = s['a'], s['b']
        zh = s.get('zh', '')
        pieces = split_one(zh, max_len)
        if len(pieces) <= 1:
            out.append({'a': round(a, 2), 'b': round(b, 2), 'zh': zh})
            continue

        # 按字数比例分配时长
        total = sum(cn_len(p) for p in pieces) or 1
        span = b - a
        t = a
        for i, p in enumerate(pieces):
            share = cn_len(p) / total
            d = span * share
            out.append({
                'a': round(t, 2),
                'b': round(t + d, 2),
                'zh': p,
            })
            t += d

    # 写回
    # 修重叠：原字幕之间本身有重叠（TTS 的 word boundary），拆分后继承了。
    # 同一时刻只能显示一条，否则两条叠在一起闪。
    for i in range(1, len(out)):
        if out[i]['a'] < out[i - 1]['b']:
            mid = (out[i]['a'] + out[i - 1]['b']) / 2
            out[i - 1]['b'] = round(mid, 2)
            out[i]['a'] = round(mid, 2)
            # 每条至少留 0.3 秒，不然闪
            if out[i - 1]['b'] - out[i - 1]['a'] < 0.3:
                out[i - 1]['a'] = round(out[i - 1]['b'] - 0.3, 2)

    sp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    js = proj / 'audio' / 'subs.js'
    js.write_text('window.SUBS = ' + json.dumps(out, ensure_ascii=False, indent=2) + ';\n',
                  encoding='utf-8')

    print(f'{proj.name}: {len(before)} 条 → {len(out)} 条')
    print()
    for s in out:
        d = s['b'] - s['a']
        print(f'  {d:4.1f}s  {len(s["zh"]):2d}字  {s["zh"]}')


if __name__ == '__main__':
    main()
