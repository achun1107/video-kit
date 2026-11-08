#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查仓库文档里的外链是否可达。

质检报告把「死链全量体检」列为「自动判不了」的项 —— 因为通用扫描器
要真去请求每个链接，容易被限流也不一定跑得完。这个脚本只查我们自己
写的链接，跳过 shields.io 徽章（那类服务本身就不稳）。

  python tools/check-links.py
  python tools/check-links.py --timeout 15
"""
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 只查这些文件里的链接
DOCS = [
    'README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md',
    'AGENTS.md', 'NOTICE',
    'docs/FAQ.md', 'docs/USAGE.md', 'docs/ARCHITECTURE.md',
]

# 这些域名不稳定或本来就慢，跳过
SKIP_HOSTS = (
    'img.shields.io',      # 徽章服务，经常 5xx 但图能显示
    'shields.io',
)

MD_LINK = re.compile(r'\[([^\]]*)\]\((https?://[^)\s]+)\)')
MD_IMG = re.compile(r'!\[([^\]]*)\]\((https?://[^)\s]+)\)')


def collect():
    links = []
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            continue
        txt = p.read_text(encoding='utf-8', errors='ignore')
        for m in MD_LINK.finditer(txt):
            links.append((rel, m.group(2), m.group(1) or '(无文字)'))
        for m in MD_IMG.finditer(txt):
            links.append((rel, m.group(2), '图片'))
    # 去重（同一个 URL 只查一次）
    seen, out = set(), []
    for f, url, label in links:
        if url in seen:
            continue
        seen.add(url)
        out.append((f, url, label))
    return out


def check(args):
    rel, url, label, timeout = args
    host = url.split('//', 1)[-1].split('/', 1)[0].lower()
    if any(h in host for h in SKIP_HOSTS):
        return (rel, url, '跳过', 0)

    req = urllib.request.Request(url, method='HEAD')
    req.add_header('User-Agent', 'Mozilla/5.0 (link-checker)')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (rel, url, r.status, 0)
    except urllib.error.HTTPError as e:
        # 有些站不支持 HEAD，退回 GET
        if e.code in (405, 403, 400):
            try:
                req2 = urllib.request.Request(url, method='GET')
                req2.add_header('User-Agent', 'Mozilla/5.0 (link-checker)')
                with urllib.request.urlopen(req2, timeout=timeout) as r2:
                    return (rel, url, r2.status, 0)
            except Exception as e2:
                return (rel, url, f'ERR {type(e2).__name__}', 1)
        return (rel, url, e.code, 1)
    except Exception as e:
        return (rel, url, f'ERR {type(e).__name__}', 1)


def main():
    timeout = 12
    if '--timeout' in sys.argv:
        timeout = int(sys.argv[sys.argv.index('--timeout') + 1])

    links = collect()
    print(f'共 {len(links)} 个外链，并发检查 …\n')

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(check, [(f, u, l, timeout) for f, u, l in links]):
            results.append(r)

    ok = [r for r in results if isinstance(r[2], int) and r[2] < 400]
    skipped = [r for r in results if r[2] == '跳过']
    bad = [r for r in results if r not in ok and r not in skipped]

    for rel, url, status, _ in ok:
        print(f'  ✓ {status}  {url[:88]}')
    for rel, url, status, _ in skipped:
        print(f'  · 跳过  {url[:88]}')

    if bad:
        print('\n✗ 有问题：')
        for rel, url, status, _ in bad:
            print(f'  {status}  {rel}  →  {url}')
        return 1

    print(f'\n✓ {len(ok)} 个可达，{len(skipped)} 个跳过，0 个死链')
    return 0


if __name__ == '__main__':
    sys.exit(main())
