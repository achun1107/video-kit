#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""扫 git 历史里的明文密钥。

为什么单独写：`test_repo_structure.py` 只扫当前工作区。
历史 commit 里的密钥就算删了文件也还在 git 对象里，
一旦推到公开仓库就是永久泄露 —— GitHub 上已经有爬虫盯着 push 事件。

  python tools/scan-history.py            # 扫全部历史
  python tools/scan-history.py --since 50 # 只扫最近 50 个 commit

只打印「文件:行号 + 命中类型」，绝不打印密钥值。
"""
import re
import subprocess
import sys

PATTERNS = {
    'GitHub PAT': r'ghp_[A-Za-z0-9]{30,}',
    'GitHub OAuth': r'gho_[A-Za-z0-9]{30,}',
    'GitHub fine-grained': r'github_pat_[A-Za-z0-9_]{50,}',
    'OpenAI key': r'sk-[A-Za-z0-9]{32,}',
    'AWS AK': r'AKIA[0-9A-Z]{16}',
    'Slack bot': r'xoxb-[0-9]{10,}-[0-9]{10,}',
    'Google API': r'AIza[0-9A-Za-z_-]{35}',
    'Private key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'JWT': r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',
}

# 这些路径里的命中多半是文档示例或扫描规则本身
ALLOWLIST = (
    'tests/',
    '.github/workflows/',
    'tools/scan-history.py',
    'docs/FAQ.md',          # FAQ 里会讲密钥格式
    'SECURITY.md',
)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw)


def main():
    since = None
    if '--since' in sys.argv:
        since = int(sys.argv[sys.argv.index('--since') + 1])

    r = run(['git', 'log', '--all', '--pretty=format:%H|%h|%an|%ad|%s',
             '--date=short'] + ([f'-{since}'] if since else []))
    commits = [l for l in (r.stdout or '').split('\n') if l.strip()]
    if not commits:
        print('没有 commit')
        return 0

    print(f'扫 {len(commits)} 个 commit …\n')

    hits = []
    seen = set()

    for line in commits:
        parts = line.split('|', 4)
        if len(parts) < 5:
            continue
        sha, short, author, date, subject = parts
        r = run(['git', 'show', '--format=', '--unified=0', sha])
        diff = r.stdout or ''
        cur_file = '?'
        cur_line = 0

        for ln in diff.split('\n'):
            if ln.startswith('+++ b/'):
                cur_file = ln[6:]
                continue
            m = re.match(r'@@ .* \+(\d+)', ln)
            if m:
                cur_line = int(m.group(1))
                continue
            if not ln.startswith('+') or ln.startswith('+++'):
                continue
            cur_line += 1

            if any(cur_file.startswith(a) for a in ALLOWLIST):
                continue

            for name, pat in PATTERNS.items():
                if re.search(pat, ln):
                    key = (cur_file, name)
                    if key in seen:
                        break
                    seen.add(key)
                    hits.append({
                        'commit': short,
                        'date': date,
                        'file': cur_file,
                        'line': cur_line,
                        'type': name,
                    })
                    break

    if not hits:
        print('✓ 历史里没有明文密钥')
        return 0

    print(f'⚠ 命中 {len(hits)} 处：\n')
    for h in hits:
        print(f"  {h['commit']}  {h['date']}  {h['file']}:{h['line']}  [{h['type']}]")

    print('\n处理方式：')
    print('  1. 确认这些值是否已失效（轮换掉）')
    print('  2. 如果仓库还没公开：用 git filter-repo 重写历史')
    print('  3. 如果已经公开：只能轮换密钥，删历史没用（别人已经 clone 了）')
    return 1


if __name__ == '__main__':
    sys.exit(main())
