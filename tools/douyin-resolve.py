# -*- coding: utf-8 -*-
"""从抖音主页 / 视频链接里找出可下载的视频（拦截 API 版）。

  python tools/douyin-resolve.py "https://v.douyin.com/wiU9DwCCETk/"
  python tools/douyin-resolve.py <url> --json out.json --max 20
"""
import sys, json, re, urllib.request
from playwright.sync_api import sync_playwright

UA_MOBILE = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
UA_DESK = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def resolve(url):
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', UA_MOBILE)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.geturl()
    except urllib.error.HTTPError as e:
        return getattr(e, 'url', url)
    except Exception:
        return url


def kind_of(u):
    if '/video/' in u:
        return 'video'
    if '/user/' in u:
        return 'user'
    return 'unknown'


def harvest(pg, bag):
    """从页面 HTML 里捞 aweme_id。"""
    try:
        html = pg.content()
    except Exception:
        return
    for m in re.finditer(r'"aweme_id"\s*:\s*"(\d{15,25})"', html):
        bag.append(m.group(1))
    for m in re.finditer(r'/video/(\d{15,25})', html):
        bag.append(m.group(1))


def collect(url, max_n=20, headless=False):
    ids = []
    api_hits = []

    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=headless,
                              args=['--disable-blink-features=AutomationControlled'])
        ctx = b.new_context(
            user_agent=UA_DESK,
            viewport={'width': 1280, 'height': 900},
            locale='zh-CN',
        )
        pg = ctx.new_page()

        def on_resp(r):
            u = r.url
            if 'aweme' in u or 'post' in u and 'douyin' in u or 'item' in u:
                try:
                    txt = r.text()
                except Exception:
                    return
                if 'aweme_id' in txt or 'aweme_list' in txt:
                    api_hits.append(u[:100])
                    for m in re.finditer(r'"aweme_id"\s*:\s*"(\d{15,25})"', txt):
                        ids.append(m.group(1))

        pg.on('response', on_resp)

        print(f'  打开 {url[:100]}')
        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f'  打开超时（继续尝试）：{str(e)[:60]}')
        pg.wait_for_timeout(6000)

        # 滚动触发懒加载
        for i in range(6):
            harvest(pg, ids)
            pg.mouse.wheel(0, 1600)
            pg.wait_for_timeout(1800)
            if len(set(ids)) >= max_n:
                break

        harvest(pg, ids)
        title = pg.title()

        # 如果当前页就是视频页，把 URL 里的 id 也算上
        m = re.search(r'/video/(\d{15,25})', pg.url)
        if m:
            ids.append(m.group(1))

        b.close()

    seen, uniq = set(), []
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        uniq.append(i)
    return uniq[:max_n], title, api_hits


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        sys.exit(__doc__)
    max_n = int(arg('--max', '20'))
    headless = '--headless' in sys.argv

    print(f'原始链接: {url}')
    real = resolve(url)
    print(f'重定向后: {real[:110]}')
    k = kind_of(real)
    print(f'类型: {k}')

    result = {'input': url, 'resolved': real, 'kind': k, 'videos': []}

    if k == 'video':
        m = re.search(r'/video/(\d+)', real)
        if m:
            result['videos'] = [{'id': m.group(1), 'url': f'https://www.douyin.com/video/{m.group(1)}'}]
    else:
        print('\n抓视频列表（拦截 API + 滚动）…')
        ids, title, apis = collect(real, max_n, headless)
        result['title'] = title
        result['api_hits'] = apis
        result['videos'] = [{'id': i, 'url': f'https://www.douyin.com/video/{i}'} for i in ids]
        print(f'主页: {title}')
        print(f'抓到 {len(ids)} 条' + (f'（命中 {len(apis)} 个接口）' if apis else ''))
        for n, v in enumerate(result['videos'][:12], 1):
            print(f'  {n:2d}. {v["id"]}  {v["url"]}')

    out = arg('--json')
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'\n写到 {out}')

    if not result['videos']:
        print('\n没抓到视频。可能原因：抖音要登录、页面结构变了、或这条分享不含视频。')


if __name__ == '__main__':
    main()
