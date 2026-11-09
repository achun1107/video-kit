# -*- coding: utf-8 -*-
"""分析对标账号 264 个作品：爆款 vs 普通款的规律。

  python tools/analyze-benchmark.py D:/douyin-benchmark.json
"""
import json
import re
import sys
from collections import Counter


def parse_like(s):
    """'1.2万' -> 12000; '141' -> 141; '' -> 0"""
    if not s:
        return 0
    s = s.strip()
    m = re.match(r'^([\d.]+)万$', s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.match(r'^([\d.]+)$', s)
    if m:
        return int(m.group(1))
    return 0


def tags(text):
    return re.findall(r'#([^\s#]+)', text)


def core(text):
    """去掉话题标签后的正文。"""
    return re.sub(r'#[^\s#]+', '', text).strip()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'D:/douyin-benchmark.json'
    data = json.loads(open(path, encoding='utf-8').read())

    for d in data:
        d['n_like'] = parse_like(d.get('like', ''))
        d['body'] = core(d.get('text', ''))
        d['tags'] = tags(d.get('text', ''))
        d['n_tags'] = len(d['tags'])

    normal = [d for d in data if not d.get('pinned')]
    pinned = [d for d in data if d.get('pinned')]

    likes = sorted([d['n_like'] for d in normal])
    n = len(likes)
    med = likes[n // 2]
    p90 = likes[int(n * 0.9)]
    p99 = likes[int(n * 0.99)] if n > 100 else likes[-1]

    print(f'共 {len(data)} 条（置顶 {len(pinned)}，普通 {n}）')
    print(f'点赞：中位数 {med}  中位以上 10% {p90}  前 1% {p99}  最高 {likes[-1]}')
    print()

    # 分桶
    buckets = Counter()
    for v in likes:
        if v >= 10000:
            buckets['1万+'] += 1
        elif v >= 5000:
            buckets['5k-1万'] += 1
        elif v >= 3000:
            buckets['3k-5k'] += 1
        elif v >= 1000:
            buckets['1k-3k'] += 1
        elif v >= 500:
            buckets['500-1k'] += 1
        elif v >= 200:
            buckets['200-500'] += 1
        else:
            buckets['<200'] += 1

    print('点赞分布：')
    for k in ['1万+', '5k-1万', '3k-5k', '1k-3k', '500-1k', '200-500', '<200']:
        v = buckets.get(k, 0)
        bar = '█' * max(0, int(v / max(1, n) * 40))
        print(f'  {k:8s} {v:4d}  {bar}')
    print()

    # 爆款 vs 普通：标题长度、标签数
    hot = [d for d in normal if d['n_like'] >= 1000]
    cold = [d for d in normal if d['n_like'] < 200]
    print(f'爆款（≥1000赞）{len(hot)} 条')
    print(f'冷门（<200赞）{len(cold)} 条')
    print()

    def avg(lst, key):
        return sum(key(d) for d in lst) / max(1, len(lst))

    print('对比：')
    print(f'  平均标题字数   爆款 {avg(hot, lambda d: len(d["body"])):.0f}  冷门 {avg(cold, lambda d: len(d["body"])):.0f}')
    print(f'  平均标签数     爆款 {avg(hot, lambda d: d["n_tags"]):.1f}  冷门 {avg(cold, lambda d: d["n_tags"]):.1f}')
    print()

    # 标签使用频率（爆款 vs 冷门）
    print('爆款常用标签 Top 15：')
    hc = Counter()
    for d in hot:
        for t in d['tags']:
            hc[t] += 1
    for t, c in hc.most_common(15):
        rate = c / max(1, len(hot))
        print(f'  #{t:16s} {c:3d} 出现在 {rate:.0%} 的爆款')
    print()

    print('冷门常用标签 Top 10：')
    cc = Counter()
    for d in cold:
        for t in d['tags']:
            cc[t] += 1
    for t, c in cc.most_common(10):
        print(f'  #{t:16s} {c:3d}')
    print()

    # 标题开头模式
    print('爆款开头 15 条：')
    for d in sorted(hot, key=lambda x: -x['n_like'])[:15]:
        print(f'  {d["n_like"]:6d}  {d["body"][:60]}')
    print()

    # 数字出现率
    def has_num(d):
        return bool(re.search(r'\d', d['body']))
    def has_q(d):
        return '？' in d['body'] or '?' in d['body']
    def has_neg(d):
        return any(w in d['body'] for w in ['别', '不', '告别', '拒绝', '傻眼', '见底', '不够', '太贵', '慢', '难'])

    print('句式特征命中率：')
    for name, fn in [('含数字', has_num), ('含问句', has_q), ('含否定/痛点词', has_neg)]:
        print(f'  {name:12s} 爆款 {sum(1 for d in hot if fn(d))/max(1,len(hot)):.0%}   冷门 {sum(1 for d in cold if fn(d))/max(1,len(cold)):.0%}')


if __name__ == '__main__':
    main()
