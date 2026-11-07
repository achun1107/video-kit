# -*- coding: utf-8 -*-
"""GitHub OAuth Device Flow —— 用户在浏览器输一个码就完成授权，不用手建 token。

  python tools/gh-device-login.py              # 只登录，打印 token 是否存在
  python tools/gh-device-login.py --push       # 登录后直接推送仓库

用的是 GitHub CLI 的公开 client_id（设备码流程本身不需要 client_secret）。
token 拿到后存进 ~/.dsh/github-token（600 权限），并在推送后把它设成 git 的 remote 凭据。
"""
import sys, json, time, urllib.request, urllib.parse, urllib.error, subprocess
from pathlib import Path

CLIENT_ID = '178c6fc778ccc68e1d6a'      # GitHub CLI 的公开 client_id
SCOPES = 'repo'
TOKEN_FILE = Path.home() / '.dsh' / 'github-token'

def post(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Accept', 'application/json')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('User-Agent', 'video-kit')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or '{}')

def api(path, token, method='GET', body=None):
    req = urllib.request.Request('https://api.github.com' + path, method=method)
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'video-kit')
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or '{}')

def main():
    do_push = '--push' in sys.argv
    repo_name = sys.argv[sys.argv.index('--repo') + 1] if '--repo' in sys.argv else 'video-kit'
    cwd = Path('.') .resolve()
    if '--dir' in sys.argv:
        cwd = Path(sys.argv[sys.argv.index('--dir') + 1]).resolve()

    # 已有 token 就直接用
    token = None
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding='utf-8').strip()
        if t:
            st, me = api('/user', t)
            if st == 200:
                token = t
                print(f'✓ 复用已保存的 token（{me.get("login")}）')

    if not token:
        # 1. 申请设备码
        st, dc = post('https://github.com/login/device/code',
                      {'client_id': CLIENT_ID, 'scope': SCOPES})
        if st != 200 or 'device_code' not in dc:
            sys.exit(f'× 申请设备码失败：{st} {dc}')
        code = dc['user_code']
        uri = dc['verification_uri']
        interval = dc.get('interval', 5)
        expires = dc.get('expires_in', 900)

        print()
        print('=' * 52)
        print('  打开这个网址：', uri)
        print('  输入这个码  ：', '  ' + code + '  ')
        print('=' * 52)
        print(f'  （{expires // 60} 分钟内有效，输完点 Authorize 即可）')
        print()

        # 2. 轮询
        deadline = time.time() + expires
        while time.time() < deadline:
            time.sleep(interval)
            st, r = post('https://github.com/login/oauth/access_token',
                         {'client_id': CLIENT_ID, 'device_code': dc['device_code'],
                          'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'})
            err = r.get('error')
            if err == 'authorization_pending':
                print('  … 等待授权', flush=True)
                continue
            if err == 'slow_down':
                interval += 5
                continue
            if err:
                sys.exit(f'× 授权失败：{err} {r.get("error_description", "")}')
            token = r.get('access_token')
            break

        if not token:
            sys.exit('× 超时未授权')

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token, encoding='utf-8')
        try:
            TOKEN_FILE.chmod(0o600)
        except Exception:
            pass
        print(f'✓ 已授权，token 存到 {TOKEN_FILE}')

    st, me = api('/user', token)
    if st != 200:
        sys.exit(f'× token 不可用：{st} {me.get("message", "")}')
    login = me['login']
    print(f'✓ 账号：{login}')

    if not do_push:
        print()
        print(f'登录完成。要推送就跑：python tools/gh-device-login.py --push --repo {repo_name}')
        return

    # 3. 建仓库
    st, info = api(f'/repos/{login}/{repo_name}', token)
    if st == 200:
        print(f'  仓库已存在：{info["html_url"]}')
    else:
        st, info = api('/user/repos', token, 'POST', {
            'name': repo_name, 'private': False,
            'description': '一条命令把 GitHub 仓库变成竖屏讲解视频',
            'auto_init': False,
        })
        if st not in (200, 201):
            sys.exit(f'× 建仓库失败：{st} {info.get("message", "")}')
        print(f'✓ 已创建：{info["html_url"]}')

    clone_url = info['clone_url']
    auth_url = clone_url.replace('https://', f'https://{login}:{token}@')

    # 4. 推送
    print(f'  推送 {cwd} → main')
    r = subprocess.run(['git', '-C', str(cwd), 'push', auth_url, 'HEAD:refs/heads/main', '--force'],
                       capture_output=True, text=True)
    print((r.stdout or '') + (r.stderr or ''))
    if r.returncode != 0:
        sys.exit('× 推送失败')

    subprocess.run(['git', '-C', str(cwd), 'remote', 'remove', 'origin'], capture_output=True)
    subprocess.run(['git', '-C', str(cwd), 'remote', 'add', 'origin', clone_url], capture_output=True)

    print()
    print(f'✓ 完成：{clone_url.replace(".git", "")}')

if __name__ == '__main__':
    main()
