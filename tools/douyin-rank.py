# -*- coding: utf-8 -*-
"""抓抖音主页视频列表，带点赞数和标题，按点赞排序。

关键：抖音主页的视频列表在 XHR 返回的 JSON 里，字段是 aweme_list，
每个元素有 aweme_id / desc / statistics.digg_count / create_time / video.duration。

  python tools/douyin-rank.py "https://v.douyin.com/xxxx/" -o rank.json --max 50
  python tools/douyin-rank.py <sec_uid> --max 50

输出按点赞数降序，每条含：
  id / title / digg / comment / share / duration_ms / url
"""
import sys, json, re, urllib.request, time
from playwright.sync_api import sync_playwright


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def resolve_short(url):
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.geturl()
    except Exception:
        return url


def walk(obj, out):
    """递归找 aweme 对象。抖音的 JSON 层级会变，靠字段特征识别。"""
    if isinstance(obj, dict):
        if 'aweme_id' in obj and ('desc' in obj or 'statistics' in obj):
            out.append(obj)
        for v in obj.values():
            walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, out)


def pick_num(d, *keys):
    st = d.get('statistics') or {}
    for k in keys:
        if k in st:
            try:
                return int(st[k])
            except Exception:
                pass
        if k in d:
            try:
                return int(d[k])
            except Exception:
                pass
    return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        sys.exit(__doc__)
    max_n = int(arg('--max', '50'))
    out_path = arg('-o', 'rank.json')

    url = resolve_short(src) if src.startswith('http') else \
        f'https://www.douyin.com/user/{src}'
    print(f'目标: {url[:100]}')

    awemes = []

    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=True,
                              args=['--disable-blink-features=AutomationControlled'])
        ctx = b.new_context(user_agent=UA, viewport={'width': 1280, 'height': 900},
                            locale='zh-CN',
                            extra_http_headers={'Referer': 'https://www.douyin.com/'})
        pg = ctx.new_page()

        def on_resp(r):
            u = r.url
            if 'douyin' not in u:
                return
            try:
                txt = r.text()
            except Exception:
                return
            if 'aweme_id' not in txt:
                return
            try:
                j = json.loads(txt)
            except Exception:
                return
            found = []
            walk(j, found)
            awemes.extend(found)

        pg.on('response', on_resp)

        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception:
            pass
        pg.wait_for_timeout(6000)

        # 滚动加载更多
        for i in range(10):
            before = len(awemes)
            pg.mouse.wheel(0, 1800)
            pg.wait_for_timeout(2200)
            ids = {(a.get('aweme_id') or '') for a in awemes}
            print(f'  滚动 {i+1}: 累计 {len(ids)} 条', flush=True)
            if len(ids) >= max_n:
                break

        title = pg.title()
        b.close()

    # 归并去重
    by_id = {}
    for a in awemes:
        aid = str(a.get('aweme_id') or '')
        if not aid or not aid.isdigit():
            continue
        prev = by_id.get(aid)
        digg = pick_num(a, 'digg_count', 'digg') or 0
        if prev is None or digg > (prev.get('_digg') or 0):
            by_id[aid] = a

    rows = []
    for aid, a in by_id.items():
        dur = None
        v = a.get('video') or {}
        if isinstance(v, dict):
            dur = v.get('duration') or v.get('duration_ms')
        rows.append({
            'id': aid,
            'title': (a.get('desc') or '').strip(),
            'digg': pick_num(a, 'digg_count', 'digg') or 0,
            'comment': pick_num(a, 'comment_count', 'comment') or 0,
            'share': pick_num(a, 'share_count', 'share') or 0,
            'duration_ms': dur,
            'create_time': a.get('create_time'),
            'url': f'https://www.douyin.com/video/{aid}',
            '_digg': pick_num(a, 'digg_count', 'digg') or 0,
        })

    rows.sort(key=lambda r: r['digg'], reverse=True)
    for r in rows:
        r.pop('_digg', None)

    data = {'source': src, 'resolved': url, 'page_title': title,
            'count': len(rows), 'videos': rows}
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n共 {len(rows)} 条，按点赞降序：')
    for i, r in enumerate(rows[:20], 1):
        t = r['title'][:38].replace('\n', ' ')
        print(f'  {i:2d}. {r["digg"]:>8,} 赞  {r["id"]}  {t}')

    print(f'\n写到 {out_path}')


if __name__ == '__main__':
    main()
