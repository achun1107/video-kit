# -*- coding: utf-8 -*-
"""从视频 ID 解析发布时间，看账号的时间趋势。

  python tools/analyze-trend.py D:/douyin-benchmark.json

## ID 结构

抖音视频 ID 是 63 位整数，**高 32 位直接是 Unix 秒级时间戳**。

  7662716941353749775 >> 32 = 1784127218  →  2026-07-13

（试过标准雪花的 shift=22 + twitter 纪元，对不上；
 shift=24 也差一年多。只有 shift=32 秒级能对上页面显示的发布时间。）

解析出来能回答：
  · 这个号是越做越好还是越做越差
  · 爆款集中在什么时期
  · 发布频率
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def video_ts(vid):
    """63 位 ID -> 北京时间。高 32 位是 Unix 秒。"""
    try:
        n = int(vid)
    except ValueError:
        return None
    sec = n >> 32
    if sec < 1577836800 or sec > 2000000000:      # 2020~2033 之外视为无效
        return None
    return datetime.fromtimestamp(sec, tz=timezone(timedelta(hours=8)))


def parse_like(s):
    if not s:
        return 0
    m = re.match(r'^([\d.]+)万$', s.strip())
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.match(r'^([\d.]+)$', s.strip())
    return int(m.group(1)) if m else 0


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'D:/douyin-benchmark.json'
    data = json.loads(open(path, encoding='utf-8').read())

    rows = []
    for d in data:
        t = video_ts(d.get('id', ''))
        if t:
            rows.append({'t': t, 'like': parse_like(d.get('like', '')),
                         'pinned': d.get('pinned', False),
                         'text': d.get('text', '')[:30]})

    if not rows:
        sys.exit('解析不出时间戳')

    rows.sort(key=lambda r: r['t'])
    print(f'解析成功 {len(rows)} / {len(data)} 条')
    print(f'时间范围：{rows[0]["t"]:%Y-%m-%d} ~ {rows[-1]["t"]:%Y-%m-%d}')
    print()

    by_month = defaultdict(list)
    for r in rows:
        by_month[r['t'].strftime('%Y-%m')].append(r['like'])

    print('按月统计：')
    print(f'{"月份":10s} {"条数":>4s} {"中位":>6s} {"均值":>7s} {"最高":>7s}')
    print('-' * 44)
    for m in sorted(by_month):
        v = sorted(by_month[m])
        print(f'{m:10s} {len(v):4d} {v[len(v)//2]:6d} {sum(v)//len(v):7d} {max(v):7d}')
    print()

    half = len(rows) // 2
    early = sorted(r['like'] for r in rows[:half])
    late = sorted(r['like'] for r in rows[half:])
    e_med = early[len(early) // 2]
    l_med = late[len(late) // 2]
    print('前后半段对比：')
    print(f'  前半（{rows[0]["t"]:%Y-%m} ~ {rows[half-1]["t"]:%Y-%m}）中位 {e_med}')
    print(f'  后半（{rows[half]["t"]:%Y-%m} ~ {rows[-1]["t"]:%Y-%m}）中位 {l_med}')
    trend = '上升' if l_med > e_med * 1.2 else ('下降' if l_med < e_med * 0.8 else '持平')
    print(f'  趋势：{trend}（{l_med / max(1, e_med):.2f}x）')
    print()

    span = (rows[-1]['t'] - rows[0]['t']).days
    print(f'发布频率：{len(rows)} 条 / {span} 天 = 平均每 {span / max(1, len(rows)):.1f} 天一条')


if __name__ == '__main__':
    main()
