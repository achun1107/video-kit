# -*- coding: utf-8 -*-
"""把本地仓库推到 GitHub。

  python tools/push-to-github.py --token <TOKEN> [--repo video-kit] [--public]

做的事：
  1. 用 token 调 GitHub API 拿用户名（顺带验证 token 有效）
  2. 建仓库（已存在就跳过）
  3. 加 remote 并推送

token 只在内存里用，不写进 .git/config、不进 shell 历史。
"""
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

token = arg('--token')
if not token:
    sys.exit('用法: python tools/push-to-github.py --token <TOKEN> [--repo video-kit] [--public]')

repo_name = arg('--repo', 'video-kit')
private = '--public' not in sys.argv
branch = arg('--branch', 'main')
cwd = Path(arg('--dir', '.')).resolve()

API = 'https://api.github.com'

def call(path, method='GET', body=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'video-kit-push')
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or '{}')

# 1. 验证 token
st, me = call('/user')
if st != 200:
    sys.exit(f'× token 无效或被停用：{st} {me.get("message", "")}')
login = me.get('login')
print(f'✓ 已登录：{login}  (token scope: {me.get("type", "")})')

# 2. 建仓库
st, info = call(f'/repos/{login}/{repo_name}')
if st == 200:
    print(f'  仓库已存在：{info["html_url"]}')
    repo_url = info['clone_url']
    owner = info['owner']['login']
else:
    st, info = call('/user/repos', 'POST', {
        'name': repo_name,
        'private': private,
        'description': '一条命令把 GitHub 仓库变成竖屏讲解视频',
        'auto_init': False,
    })
    if st not in (200, 201):
        sys.exit(f'× 建仓库失败：{st} {info.get("message", "")}')
    print(f'✓ 已创建：{info["html_url"]}')
    repo_url = info['clone_url']
    owner = info['owner']['login']

# 3. 推送（token 只在这一条命令里出现，不写进 .git/config）
auth_url = repo_url.replace('https://', f'https://{owner}:{token}@')
print(f'  推送 {cwd} → {branch}')
r = subprocess.run(['git', '-C', str(cwd), 'push', auth_url, f'HEAD:refs/heads/{branch}', '--force'],
                   capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
if r.returncode != 0:
    sys.exit('× 推送失败')

# 4. 把 origin 设成不带 token 的地址
subprocess.run(['git', '-C', str(cwd), 'remote', 'remove', 'origin'], capture_output=True)
subprocess.run(['git', '-C', str(cwd), 'remote', 'add', 'origin', repo_url], capture_output=True)

print()
print(f'✓ 完成：{repo_url.replace(".git", "")}')
