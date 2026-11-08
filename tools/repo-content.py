# -*- coding: utf-8 -*-
"""用 GitHub API 生成 content.json，不 clone 仓库。

clone 大仓库经常 180 秒超时，这个脚本走 API 拿元信息和 README，
足够填满七张卡。

  python tools/repo-content.py <owner/repo 或 URL> -o content.json
  python tools/repo-content.py heygen-com/hyperframes -o content.json --token ghp_xxx
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def api(path, token=None):
    req = urllib.request.Request('https://api.github.com' + path)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'video-kit')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or '{}')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        sys.exit(__doc__)
    m = re.search(r'github\.com/([^/\s]+/[^/\s#?]+)', src)
    slug = (m.group(1) if m else src).rstrip('/').replace('.git', '')
    token = arg('--token') or None
    out = Path(arg('-o', 'content.json'))

    st, repo = api('/repos/' + slug, token)
    if st != 200:
        sys.exit(f'× 拿不到 {slug}：{st} {repo.get("message","")}')

    owner, name = slug.split('/')

    # README
    body = ''
    st2, rd = api(f'/repos/{slug}/readme', token)
    if st2 == 200 and rd.get('content'):
        try:
            body = base64.b64decode(rd['content']).decode('utf-8', 'ignore')
        except Exception:
            body = ''

    # 从 README 抽小节标题做 features
    heads = re.findall(r'^#{2,3}\s+(.+?)\s*$', body, re.M)
    skip = {'install', 'installation', '安装', 'license', 'license)', 'contributing', 'acknowledgements',
            'changelog', 'credits', 'footer', 'table of contents', 'contents', '目录'}
    feats = []
    for h in heads:
        h2 = re.sub(r'[`*_\[\]()#]', '', h).strip()
        if not h2 or len(h2) > 24:
            continue
        if h2.lower() in skip:
            continue
        feats.append(h2)
    feats = feats[:6]

    # 首段做 tagline
    desc = (repo.get('description') or '').strip()
    tagline = desc
    if not tagline:
        for line in body.split('\n'):
            line = line.strip()
            if line and not line.startswith(('#', '!', '[', '<', '|', '-', '*', '`')):
                tagline = re.sub(r'[`*_\[\]()]', '', line)[:60]
                break

    # 猜 emoji
    emoji = '📦'
    low = (name + ' ' + desc).lower()
    for k, e in [('video', '🎬'), ('frame', '🎞️'), ('render', '🎬'), ('motion', '🎥'),
                 ('agent', '🤖'), ('llm', '🧠'), ('theme', '🎨'), ('color', '🎨'),
                 ('music', '🎵'), ('audio', '🎧'), ('scrap', '🕷️'), ('crawl', '🕷️'),
                 ('kanban', '🧭'), ('doc', '📚'), ('kit', '🧰')]:
        if k in low:
            emoji = e
            break

    data = {
        'repo': slug,
        'namePlain': repo.get('name') or name,
        'emoji': emoji,
        'headline': (tagline or desc or name)[:40],
        'tagline': tagline[:60],
        'version': '',
        'accent': '#E8613C',
        'accent2': '#6FE04A',
        'stats': {
            'star': repo.get('stargazers_count', 0),
            'fork': repo.get('forks_count', 0),
        },
        'statLabels': {'star': 'Star', 'fork': 'Fork'},
        'features': [{'title': f} for f in feats],
        'chapters': [],
        'conclusion': ['完全开源', f"{repo.get('stargazers_count',0)} Star", '拿来就用'],
        'topics': repo.get('topics', [])[:8],
        'lang': repo.get('language') or '',
        'license': (repo.get('license') or {}).get('spdx_id') or '',
        'homepage': repo.get('homepage') or '',
    }

    # headline 如果是纯英文，念出来很怪（TTS 会一个词一个词念）。
    # 这里只提示，不自动翻译 —— 翻译需要人判断哪个词是卖点。
    import re as _re
    if data['headline'] and not _re.search(r'[\u4e00-\u9fa5]', data['headline']):
        print()
        print('  ⚠ headline 是英文：' + data['headline'])
        print('    配音会把每个英文词单独念出来，听着别扭。')
        print('    建议在 content.json 里手改 headline 为一句中文卖点。')

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✓ {out}')
    print(f'  {data["namePlain"]}  [{data["stats"]["star"]} star / {data["stats"]["fork"]} fork]')
    print(f'  一句话: {data["headline"]}')
    if feats:
        print(f'  特性 {len(feats)} 条: ' + ' / '.join(feats[:6]))
    if data['topics']:
        print('  标签: ' + ', '.join(data['topics']))


if __name__ == '__main__':
    main()
