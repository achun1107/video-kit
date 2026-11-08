# -*- coding: utf-8 -*-
"""从转写文本反查 GitHub 仓库。

核心思路：口播里经常报 star 数（"3.6万star"、"一点八万star"），
这个数字是独一无二的指纹。配合关键词搜索 GitHub，再用 star 数校验，
比正则找 owner/repo 可靠得多。

  python tools/repo-finder.py <asr.json> [--title "..."] [-o out.json]
  python tools/repo-finder.py douyin/asr/xxx.json --title "紫微斗数" -o found.json

输出候选列表，按「star 接近度 + 关键词命中」排序。
"""
import sys, json, re, os, urllib.request, urllib.parse, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asrfix import fix_text, clean_keywords


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


TOKEN = os.environ.get('GITHUB_TOKEN')


def api(path):
    req = urllib.request.Request('https://api.github.com' + path)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'video-kit')
    if TOKEN:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {'message': str(e)}
    except Exception as e:
        return {'message': str(e)}


# ────────────── 中文数字 ──────────────

CN_DIGIT = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
CN_UNIT = {'十': 10, '百': 100, '千': 1000}

# whisper 常把数字听成别的字
HOMOPHONE = {'点': '.', '': ''}


def parse_cn_number(s):
    """'3.6' / '一点八' / '1.05' / '三万六' → float"""
    s = s.strip()
    if not s:
        return None

    # 纯阿拉伯数字（可能带小数点）
    m = re.fullmatch(r'(\d+(?:\.\d+)?)', s)
    if m:
        return float(m.group(1))

    # 阿拉伯 + 中文点（"3点6"）
    m = re.fullmatch(r'(\d+)\s*[点\.]\s*(\d+)', s)
    if m:
        return float(f'{m.group(1)}.{m.group(2)}')

    # 中文数字："一点八" → 1.8
    m = re.fullmatch(r'([一二两三四五六七八九零])\s*点\s*([零一二三四五六七八九]+)', s)
    if m:
        whole = CN_DIGIT.get(m.group(1), 0)
        frac = ''.join(str(CN_DIGIT.get(c, 0)) for c in m.group(2))
        return float(f'{whole}.{frac}')

    # "一百八" = 180，"一千三" = 1300（省略末位单位）
    # 必须特判：通用循环会把它算成 100 + 8 = 108
    m = re.fullmatch(r'([一二两三四五六七八九])([百千])([一二两三四五六七八九])', s)
    if m:
        base = CN_DIGIT[m.group(1)] * CN_UNIT[m.group(2)]
        unit = CN_UNIT[m.group(2)] // 10
        return float(base + CN_DIGIT[m.group(3)] * unit)

    # "三万六" 这类省略末位单位的说法：= 3万 + 6千
    # 必须在通用循环前特判，否则循环会把末尾的"六"当个位加进去，得到 30006
    m = re.fullmatch(r'([一二两三四五六七八九])万([一二两三四五六七八九])', s)
    if m:
        return float(CN_DIGIT[m.group(1)] * 10000 + CN_DIGIT[m.group(2)] * 1000)

    # 通用累加：十八 → 18
    total, section, last = 0, 0, 0
    touched = False
    for ch in s:
        if ch in CN_DIGIT:
            last = CN_DIGIT[ch]
            touched = True
        elif ch in CN_UNIT:
            u = CN_UNIT[ch]
            if last == 0:
                last = 1
            section += last * u
            last = 0
            touched = True
        elif ch == '万':
            section += last
            total += section * 10000
            section, last = 0, 0
            touched = True
        elif ch == '亿':
            section += last
            total = (total + section) * 100000000
            section, last = 0, 0
            touched = True
    if not touched:
        return None
    section += last
    return float(total + section)


def find_star_hint(text):
    """从文本里找 star 数。返回 (数值, 原始片段) 列表。

    只认明确跟着 star / 星 / 标 的数字。
    早先还额外抓所有「N万」——那会把「67.5万张命盘」当成 star 数，
    结果 44 万 star 的无关仓库匹配度反而最高。宁可少抓，不能错抓。
    """
    hits = []
    num = r'((?:\d+(?:\.\d+)?)|(?:[零一二两三四五六七八九十百千万亿]+(?:\.[\d]+)?)|(?:[一二两三四五六七八九]点[零一二三四五六七八九]+))'
    for m in re.finditer(num + r'\s*万?\s*(?:个)?\s*(?:star|Star|STAR|星|行标|新标)', text):
        raw = m.group(0)
        n = parse_cn_number(m.group(1))
        if n is None:
            continue
        if '万' in raw:
            n *= 10000
        if n >= 100:
            hits.append((int(n), raw))

    # 去重
    seen, out = set(), []
    for n, raw in hits:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, raw))
    return out


# ────────────── 关键词 ──────────────

STOP_CN = set('这个那个一个什么可以就是不是还有然后所以但是因为如果虽然我的你的他的'
              '已经能够支持使用起来进去出来时候东西一起一样非常特别真的确实比较'
              '功能项目开源框架工具直接自动全部完全免费大家我们你们他们现在知道')
STOP_EN = set('the and for you with this that can not are was were codex gpt ai skill skills '
              'github star mcp api app use using open source'.split())


# 公司 / 组织 → GitHub org。口播里提公司名是最强的定位线索。
ORG_MAP = {
    '字节': 'bytedance', '字节跳动': 'bytedance', '抖音': 'bytedance',
    '微软': 'microsoft', '温软': 'microsoft',
    '阿里': 'alibaba', '阿里巴巴': 'alibaba',
    '腾讯': 'Tencent',
    '百度': 'baidu',
    '谷歌': 'google',
    '华为': 'huaweicloud',
    '商汤': 'SenseTime',
    '智谱': 'THUDM',
    '月之暗面': 'MoonshotAI',
    '月暗': 'MoonshotAI',
}


def find_org(text):
    """从文本里找公司名，返回 GitHub org。"""
    for cn, org in ORG_MAP.items():
        if cn in text:
            return org
    return None


def keywords(text, title):
    """提取搜索关键词。

    jieba.analyse.extract_tags 走 TF-IDF，比词性筛选稳：
    词性筛选会把"紫微斗数"这种 n 类专名漏掉，TF-IDF 不会。
    """
    import jieba
    import jieba.analyse

    kws = []

    # 1. 标题里的英文词（抖音标题人工写，最可信）
    for w in re.findall(r'[A-Za-z][A-Za-z0-9_\-]{2,}', title or ''):
        if w.lower() not in STOP_EN:
            kws.append(w)

    # 2. TF-IDF 关键词
    try:
        for w in jieba.analyse.extract_tags(text, topK=20):
            kws.append(w)
    except Exception:
        pass

    # 3. 正文里的英文专名
    for w in re.findall(r'[A-Za-z][A-Za-z0-9_\-]{2,}', text):
        if w.lower() not in STOP_EN and len(w) >= 3:
            kws.append(w)

    # 去重保序
    seen, out = set(), []
    for k in kws:
        k2 = k.lower().strip()
        if not k2 or k2 in seen:
            continue
        seen.add(k2)
        out.append(k.strip())
    return clean_keywords(out)[:24]



# ────────────── 搜索 ──────────────

def search(q, per_page=8):
    p = '/search/repositories?' + urllib.parse.urlencode({
        'q': q, 'sort': 'stars', 'order': 'desc', 'per_page': per_page})
    r = api(p)
    return r.get('items') or []


def score(repo, hints, kws, title, org=None):
    """star 接近度 + 描述命中 + org 命中。

    star 只是辅助：口播里的数字可能过时（涨了），而且容易和别的数字混淆。
    真正可靠的是「关键词是否出现在仓库名/描述/话题里」。
    """
    s = 0.0
    star = repo.get('stargazers_count') or 0

    # star 接近度。
    # 上限放到 2.0 倍：口播报的数字往往过时，项目后来涨一倍很常见
    # （紫微斗数那条口播 1.05 万，实际已经 1.67 万，卡 1.4 倍反而把它筛掉）。
    for h, _ in hints:
        if h <= 0:
            continue
        ratio = star / h
        if 0.8 <= ratio <= 2.0:
            s += 40
            s += 60 * (1 - min(abs(1 - ratio), 1)) ** 1.5
        elif 0.5 <= ratio <= 3.0:
            s += 25

    full_name = (repo.get('full_name') or '').lower()
    name_only = full_name.split('/')[-1]
    owner = full_name.split('/')[0]
    desc = (repo.get('description') or '').lower()
    topics = ' '.join(repo.get('topics') or []).lower()

    # org 命中：最硬的线索之一
    if org and owner == org.lower():
        s += 30

    # 关键词命中（描述 > 名字 > 话题）。
    # 上限 45：原来给到 70 时，描述里堆了一堆泛词（github / 科技 / 生活）
    # 的仓库能压过真正对口的那个。
    hit = 0
    for k in kws:
        kl = k.lower()
        if len(kl) < 2:
            continue
        if kl in desc:
            hit += 5
        if kl in name_only:
            hit += 10
        if kl in topics:
            hit += 3
    s += min(hit, 45)

    # 标题里的英文词命中
    for w in re.findall(r'[A-Za-z][A-Za-z0-9_\-]{2,}', title or ''):
        wl = w.lower()
        if wl in full_name:
            s += 20
        elif wl in desc:
            s += 8

    return s



def main():
    asr_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not asr_path:
        sys.exit(__doc__)
    asr = json.loads(open(asr_path, encoding='utf-8').read())
    text = asr.get('full') or ''
    title = arg('--title', '')

    # whisper 的误听先纠正（Gatehub→GitHub、紫围斗树→紫微斗数…），
    # 不纠正的话关键词和 star 线索都是错的
    text_fixed = fix_text(text)
    title_fixed = fix_text(title)

    org = find_org(text_fixed) or find_org(title_fixed)
    hints = find_star_hint(text_fixed)
    kws = keywords(text_fixed, title_fixed)
    kws = clean_keywords(kws)

    print(f'公司/组织：{org or "未提及"}')
    print(f'star 线索：{hints if hints else "无"}')
    print(f'关键词 {len(kws)} 个：{", ".join(kws[:14])}')

    # 组 query：优先用「专名 + 功能词」
    queries = []
    # org 搜索优先级最高
    if org:
        queries.append(f'org:{org} stars:>1000')
        for kw in kws[:2]:
            queries.append(f'org:{org} {kw}')
    for n, _ in hints[:2]:
        for kw in kws[:4]:
            queries.append(f'{kw} stars:>1000')
    for kw in kws[:6]:
        queries.append(f'{kw} stars:>2000')
    if not queries:
        queries = ['stars:>3000']

    seen_q, uniq_q = set(), []
    for q in queries:
        if q in seen_q:
            continue
        seen_q.add(q)
        uniq_q.append(q)

    cands = {}
    for q in uniq_q[:8]:
        items = search(q)
        if not items:
            continue
        print(f'  「{q}」→ {len(items)} 条')
        for it in items:
            fn = it.get('full_name')
            if fn and fn not in cands:
                cands[fn] = it

    scored = sorted(cands.items(), key=lambda kv: -score(kv[1], hints, kws, title, org))

    print(f'\n候选 {len(scored)} 个，前 6：')
    out_rows = []
    for fn, it in scored[:6]:
        sc = score(it, hints, kws, title, org)
        desc = (it.get('description') or '').replace('\n', ' ')[:60]
        print(f'  {sc:6.1f}  {it["stargazers_count"]:>8,}  {fn}  {desc}')
        out_rows.append({'full_name': fn, 'stars': it['stargazers_count'],
                         'score': round(sc, 1), 'desc': desc})

    # 置信度判定。
    # 只有「绝对分够高」且「领先第二名够多」才算认出来。
    # 否则宁可说没找到 —— 一条讲 ChatGPT 内置功能的视频，
    # 硬凑出来的仓库比空着更误导人。
    best = None
    confident = False
    if scored:
        top_fn, top_it = scored[0]
        top_sc = score(top_it, hints, kws, title, org)
        second_sc = score(scored[1][1], hints, kws, title, org) if len(scored) > 1 else 0
        margin = top_sc - second_sc
        if top_sc >= 60 and margin >= 4:
            best, confident = top_fn, True
            print(f'\n✓ 最可能：{top_fn}  （{top_sc:.1f} 分，领先 {margin:.1f}）')
        else:
            print(f'\n? 候选里 {top_fn} 分最高（{top_sc:.1f}），但'
                  f'{"分差不够" if top_sc >= 50 else "绝对分太低"}'
                  f'（领先 {margin:.1f}），不自动采信')
            print('  这条视频可能讲的不是某个具体 GitHub 仓库，或者需要人工确认')

    out = arg('-o')
    if out:
        open(out, 'w', encoding='utf-8').write(json.dumps({
            'asr': asr_path, 'title': title, 'org': org, 'star_hints': hints,
            'keywords': kws, 'best': best, 'confident': confident,
            'candidates': out_rows,
        }, ensure_ascii=False, indent=2))
        print(f'写到 {out}')

    return 0 if confident else 1


if __name__ == '__main__':
    main()
