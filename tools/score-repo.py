# -*- coding: utf-8 -*-
"""选题评估：这个仓库值不值得做视频。

  python tools/score-repo.py owner/repo
  python tools/score-repo.py webkubor/xiaobai-kanban
  python tools/score-repo.py owner/a owner/b owner/c   （批量对比）

## 为什么需要这个

工作流能把画面做到很精致，但**项目本身没吸引力，天花板就在那里**。
133 星的小工具，画面再好也难火。

做视频前先问一句：这项目值得占我 30 秒吗？

## 评分维度（满分 10）

  star 数        0-3    社会证明。1000+ 才有点话题性，100 以下基本没戏
  增长速度        0-2    最近一个月有新 commit 说明还活着
  可视化          0-2    有截图/UI 就好做，纯 CLI 很难出画面
  一句话说清      0-2    description 能不能让人秒懂
  赛道热度        0-1    AI / 效率工具 / 爬虫 比 "个人博客模板" 有流量

## 输出建议

  ≥7   值得做，数据大概率不错
  5-6  能做，但要找到独特角度
  <5   不建议，除非有特别的故事
"""
import json
import os
import sys
import urllib.request

# 热门赛道关键词（有流量的方向）
HOT_KEYWORDS = [
    'ai', 'agent', 'llm', 'gpt', 'claude', 'chatgpt', 'copilot', 'mcp',
    '自动化', '爬虫', 'scraping', 'crawler',
    '效率', 'productivity', 'workflow', '自动化工具',
    '视频', 'video', '剪辑', '渲染', 'render',
    '可视化', 'visualization', '图表', 'chart',
    '低代码', 'no-code', 'nocode',
]

# 冷门赛道（流量差）
COLD_KEYWORDS = [
    '模板', 'template', '主题', 'theme', '博客', 'blog',
    '脚手架', 'boilerplate', 'starter',
    '练习', 'demo', 'tutorial', 'example', '学习笔记',
    'awesome', '清单', 'collection',
]


def api(path, token=None):
    url = f'https://api.github.com{path}'
    headers = {'User-Agent': 'video-kit-scorer', 'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RuntimeError(
                'GitHub API 限流（403）。等一会儿再试，或者设 GITHUB_TOKEN 环境变量'
            ) from e
        raise


def score(repo, token=None):
    """返回 (总分, 明细列表, 建议)。"""
    data = api(f'/repos/{repo}', token)

    star = data.get('stargazers_count', 0)
    desc = (data.get('description') or '').strip()
    lang = data.get('language') or ''
    forks = data.get('forks_count', 0)
    issues = data.get('open_issues_count', 0)
    topics = data.get('topics') or []
    homepage = data.get('homepage') or ''
    pushed = data.get('pushed_at') or ''
    created = data.get('created_at') or ''

    detail = []
    total = 0.0

    # ── star 数（0-3）──
    if star >= 10000:
        s = 3.0
    elif star >= 3000:
        s = 2.5
    elif star >= 1000:
        s = 2.0
    elif star >= 300:
        s = 1.2
    elif star >= 100:
        s = 0.6
    else:
        s = 0.1
    total += s
    detail.append(('star 数', s, 3, f'{star:,}'))

    # ── 活跃度（0-2）：看最后 push 时间 ──
    s = 0.0
    note = '无数据'
    if pushed:
        from datetime import datetime, timezone
        try:
            t = datetime.fromisoformat(pushed.replace('Z', '+00:00'))
            days = (datetime.now(timezone.utc) - t).days
            if days <= 7:
                s, note = 2.0, '一周内有更新'
            elif days <= 30:
                s, note = 1.5, f'{days} 天前更新'
            elif days <= 90:
                s, note = 1.0, f'{days} 天前更新'
            elif days <= 365:
                s, note = 0.4, f'{days} 天前更新（偏旧）'
            else:
                s, note = 0.0, f'{days} 天前更新（很久没动）'
        except Exception:
            note = pushed[:10]
    total += s
    detail.append(('活跃度', s, 2, note))

    # ── 可视化（0-2）：有 homepage 或有截图类文件 ──
    s = 0.0
    notes = []
    if homepage:
        s += 1.0
        notes.append('有在线 Demo')
    if any(k in desc.lower() for k in ('ui', 'interface', 'dashboard', '界面', '看板', '可视化')):
        s += 0.6
        notes.append('描述里提到界面')
    if lang in ('TypeScript', 'JavaScript', 'HTML', 'CSS', 'Vue'):
        s += 0.4
        notes.append(f'前端项目（{lang}）')
    s = min(s, 2.0)
    total += s
    detail.append(('可视化', s, 2, '、'.join(notes) if notes else '纯命令行/后端，画面难做'))

    # ── 一句话说清（0-2）──
    s = 0.0
    n = len(desc)
    if 10 <= n <= 60:
        s = 2.0
        note = f'{n} 字，长度合适'
    elif 60 < n <= 100:
        s = 1.2
        note = f'{n} 字，偏长'
    elif n > 100:
        s = 0.5
        note = f'{n} 字，太长'
    elif n > 0:
        s = 0.8
        note = f'{n} 字，太短'
    else:
        note = '没有 description'
    total += s
    detail.append(('一句话说清', s, 2, note))

    # ── 赛道热度（0-1）──
    blob = (desc + ' ' + ' '.join(topics) + ' ' + (data.get('name') or '')).lower()
    hot = [k for k in HOT_KEYWORDS if k in blob]
    cold = [k for k in COLD_KEYWORDS if k in blob]
    if hot and not cold:
        s, note = 1.0, f'热门方向（{hot[0]}）'
    elif hot:
        s, note = 0.5, f'有热门词（{hot[0]}）但也有冷门词（{cold[0]}）'
    elif cold:
        s, note = 0.0, f'冷门方向（{cold[0]}）'
    else:
        s, note = 0.4, '中性方向'
    total += s
    detail.append(('赛道热度', s, 1, note))

    # ── 建议 ──
    if total >= 7:
        advice = '值得做。数据大概率不错。'
    elif total >= 5:
        advice = '能做，但要找到独特角度 —— 光说"有个开源项目"没人看。'
    else:
        advice = '不建议。除非你在这个项目里有故事（自己做的、踩过坑、正在用）。'

    return round(total, 1), detail, advice, {
        'desc': desc, 'star': star, 'forks': forks, 'issues': issues,
        'lang': lang, 'homepage': homepage, 'topics': topics,
        'created': created[:10], 'pushed': pushed[:10],
    }


def main():
    repos = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not repos:
        sys.exit(__doc__)

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print('（没设 GITHUB_TOKEN，可能被限流）\n')

    results = []
    for r in repos:
        try:
            total, detail, advice, info = score(r, token)
            results.append((r, total, detail, advice, info))
        except Exception as e:
            print(f'{r}: 失败 — {e}')
            continue

    results.sort(key=lambda x: -x[1])

    for repo, total, detail, advice, info in results:
        print('=' * 62)
        print(f'{repo}   {total}/10')
        print('=' * 62)
        print(f'  {info["desc"][:70]}')
        print(f'  {info["star"]:,} star · {info["forks"]:,} fork · '
              f'{info["lang"] or "?"} · {info["created"]} 建 · {info["pushed"]} 更新')
        if info['homepage']:
            print(f'  Demo: {info["homepage"][:60]}')
        print()
        for name, got, full, note in detail:
            bar = '█' * int(got / full * 12) if full else ''
            print(f'  {name:10s} {got:3.1f}/{full:.0f}  {bar:<12s} {note}')
        print()
        print(f'  → {advice}')
        print()

    if len(results) > 1:
        print('=' * 62)
        print('排名')
        print('=' * 62)
        for i, (repo, total, _, _, _) in enumerate(results, 1):
            print(f'  {i}. {repo:40s} {total}/10')


if __name__ == '__main__':
    main()
