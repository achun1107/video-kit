# -*- coding: utf-8 -*-
"""上传 demo.mp4 到 GitHub Release 附件。

curl 的 --data-binary 对 8MB 二进制不太稳，用 urllib 直接发。
"""
import json
import os
import urllib.request
import urllib.error

TOKEN = os.environ.get('GITHUB_TOKEN', '')
if not TOKEN:
    raise SystemExit('需要 GITHUB_TOKEN')

REPO = 'achun1107/video-kit'
TAG = 'v1.0.0'
NAME = 'demo.mp4'
SRC = r'D:\DSH\achun\video-hyperframes\renders\final.mp4'


def api(path, method='GET', body=None):
    req = urllib.request.Request('https://api.github.com' + path, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'vk')
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        return {'_error': e.code, '_body': e.read().decode()[:300]}


rel = api(f'/repos/{REPO}/releases/tags/{TAG}')
if '_error' in rel:
    raise SystemExit(f'拿不到 release：{rel}')

print(f"release: {rel['tag_name']}  {rel['html_url']}")

# 已有同名附件就先删（重跑时）
for a in rel.get('assets', []):
    if a['name'] == NAME:
        api(f"/repos/{REPO}/releases/assets/{a['id']}", 'DELETE')
        print(f"  删掉旧的 {NAME}")

size = os.path.getsize(SRC)
print(f'  上传 {NAME}  {size/1048576:.2f} MB')

upload_url = rel['upload_url'].split('{')[0]
with open(SRC, 'rb') as f:
    data = f.read()

req = urllib.request.Request(f'{upload_url}?name={NAME}', data=data, method='POST')
req.add_header('Authorization', 'Bearer ' + TOKEN)
req.add_header('Content-Type', 'video/mp4')
req.add_header('Content-Length', str(size))
req.add_header('User-Agent', 'vk')

try:
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
        print(f"✓ {d['name']}  {d['size']/1048576:.2f} MB")
        print(f"  {d['browser_download_url']}")
except urllib.error.HTTPError as e:
    print('×', e.code, e.read().decode()[:400])
    raise SystemExit(1)
