# -*- coding: utf-8 -*-
"""生成两档文案：模板稿 + 参考稿。

  python tools/script-writer.py <工程目录>
  python tools/script-writer.py <工程目录> --from-asr douyin/asr/xxx.json --style mixed

产出 audio/copy.json：
  {
    "variants": {
      "template": {"vo1": "...", "vo2": "..."},
      "reference": {"vo1": "...", "vo2": "..."}   ← 有 --from-asr 时才有
    },
    "vo1": ..., "vo2": ...       ← 最终采用的那一档（默认 template）
  }

两档的区别：
  模板稿   —— 只读 content.json，套固定话术骨架。永远能出片，但信息密度低。
  参考稿   —— 读原视频转写，借用它的结构和节奏，把主语换成目标项目。
             有原片时质量明显更高，因为借的是别人验证过的讲法。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asrfix import fix_text


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def clean(s):
    return re.sub(r'\s+', '', s or '')


def cn_len(s):
    return len(clean(s))


# 受众句式：这些是「适合谁」，不是「能做什么」。
# 念进配音里会文不对题（「它主要能做这几件事：给真人、给不想花钱的人」）。
AUDIENCE_RE = re.compile(
    r'^(给|适合|面向|针对)'
    r'|.*(的人|用户|同学|新手|小白)$'
)


# ────────────────────────── 模板稿 ──────────────────────────

HOOKS = [
    '还在手动做视频吗？',
    '这个开源项目，值得花两分钟看看。',
    '如果你也在用 AI 干活，这个别错过。',
    '又发现一个能省时间的东西。',
]

# 四种风格的文案骨架。同一项目用不同骨架，音频才不会撞。
STYLE_BONES = {
    # 教学语气：先承认"这是个什么东西"，再带看
    'ajin': {
        'hook': '今天带你看一个开源项目',
        'open': '{name}，{head}。',
        'feat': '它主要能做这几件事：{items}。',
        'data': 'GitHub 上已经有 {star} 个 star，代码全部公开。',
        'close': '想试的话，搜 {name} 就能找到，装上就能用。',
    },
    # 划重点语气：先说结论，再展开
    'ganhuoju': {
        'hook': '先说结论',
        'open': '这个叫 {name} 的项目，{head}。',
        'feat': '重点在这几块：{items}。',
        'data': '{star} 星，不算多，但能用的东西都齐了。',
        'close': '仓库名我放在最后，自己去搜。',
    },
    # 推荐语气：像在跟朋友分享
    'xiaokai': {
        'hook': '又挖到一个宝藏开源项目',
        'open': '{name}，一句话概括就是：{head}。',
        'feat': '我自己觉得最有用的三个点：{items}。',
        'data': '现在 {star} 星，还比较冷门。',
        'close': '想看的搜仓库名，免费的。',
    },
    # 产品语气：像发布会介绍
    # 字数要够（配音撑满 34.8 秒），所以多两句：适用场景 + 门槛
    'weitu': {
        'hook': '刚开源',
        'open': '{name}，{head}。',
        'feat': '核心能力包括：{items}。',
        'scene': '用得上的场景挺多，自己折腾项目、团队内部工具、给别人交付，都能省事。',
        'data': '项目上线不久，GitHub 上已经拿到 {star} 星。',
        'close': '完全开源，装上就能跑，不挑系统。',
    },
}


def styled_script(c, style):
    """按风格骨架生成文案。没有对应风格就往回退到通用模板。"""
    bone = STYLE_BONES.get(style)
    if not bone:
        return None

    name = c.get('namePlain') or c.get('name') or '这个项目'
    head = (c.get('headline') or '').strip()
    stats = c.get('stats') or {}
    star = stats.get('star')
    feats = c.get('features') or []
    concl = c.get('conclusion') or []

    # 过滤受众描述：「给真人（小白）」「给不想花钱的人」这类是「适合谁」，
    # 不是「能做什么」，念出来文不对题
    items = []
    for f in feats:
        t = f.get('title') if isinstance(f, dict) else str(f)
        t = str(t or '').strip().rstrip('。')
        if not t or len(t) < 4:
            continue
        if AUDIENCE_RE.match(t):
            continue
        items.append(t)
        if len(items) >= 3:
            break
    items_s = '、'.join(items) if items else ''

    head_s = head.rstrip('。') if head else '一个开源项目'
    star_s = f'{star:,}' if star else '几百'

    p1 = [
        bone['hook'] + '。',
        bone['open'].format(name=name, head=head_s),
    ]
    if items:
        p1.append(bone['feat'].format(items=items_s))
    if bone.get('scene'):
        p1.append(bone['scene'])
    if star:
        p1.append(bone['data'].format(star=star_s))

    p2 = []
    if concl:
        p2.append('总结：' + '，'.join(str(x) for x in concl[:3]) + '。')
    p2.append(bone['close'].format(name=name))

    return {'vo1': ''.join(p1), 'vo2': ''.join(p2)}


def template_script(c):
    name = c.get('namePlain') or c.get('name') or '这个项目'
    head = (c.get('headline') or '').strip()
    tag = (c.get('tagline') or '').strip()
    stats = c.get('stats') or {}
    feats = c.get('features') or []
    concl = c.get('conclusion') or []
    star = stats.get('star')

    hook = HOOKS[0]
    if star and star > 10000:
        hook = f'{star:,} 星的开源项目，你还没用过？'

    # vo1：钩子 + 是什么 + 三个亮点
    p1 = [hook]
    if head:
        p1.append(f'{name}，{head.rstrip("。")}。')
    elif tag:
        p1.append(f'{name}，{tag.rstrip("。")}。')

    titles = []
    for f in feats[:3]:
        t = f.get('title') if isinstance(f, dict) else str(f)
        if t:
            titles.append(t.rstrip('。'))
    if titles:
        p1.append('它主要有这几样：' + '、'.join(titles) + '。')

    if star:
        p1.append(f'GitHub 上 {star:,} 个 star，代码全部公开。')

    vo1 = ''.join(p1)

    # vo2：怎么用 + 结论
    p2 = []
    if concl:
        p2.append('总结一下：' + '，'.join(str(x) for x in concl[:3]) + '。')
    p2.append(f'想试的话，搜 {name} 就能找到仓库，装上就能用。')
    vo2 = ''.join(p2)

    return {'vo1': vo1, 'vo2': vo2}


# ────────────────────────── 参考稿 ──────────────────────────

def reference_script(c, asr):
    """从原片转写里抽话术骨架，换主语。

    为什么这么做：原片的文案是别人验证过能留住人的，它的**句子顺序、
    信息密度、钩子位置**比模板套话值钱。我们要的是这个骨架，
    内容（名字、功能、数字）换成目标仓库的。

    三步：
      1. 挑信息量大的句子（含数字 / 含功能动词 / 不是纯语气）
      2. 把原片专名换成目标项目名
      3. 按目标字数取舍（vo1 约 20 秒，vo2 约 11 秒）
    """
    name = c.get('namePlain') or c.get('name') or '这个项目'
    head = (c.get('headline') or '').strip()
    tag = (c.get('tagline') or '').strip()
    stats = c.get('stats') or {}
    star = stats.get('star')
    segs = asr.get('segments') or []
    full = asr.get('full') or ''

    if not segs:
        return None

    total = segs[-1].get('end', 0) or 0
    chars = asr.get('chars') or cn_len(full)
    rate = asr.get('rate') or (chars / max(total, .1))
    cap1 = int(rate * 20)
    cap2 = int(rate * 12)

    # ── 1. 挑句子 ──
    # 哪些算「信息量大」：带数字、带功能动词、长度 12-40 字
    FUNC_WORDS = ('装上', '装上', '生成', '自动', '接管', '批量', '支持', '适合',
                  '专门', '直接', '不用', '只要', '就能', '一句话', '开源', '免费')
    BORING = ('不知道', '怎么玩', '厉害', '真正')

    def info_score(t):
        sc = 0
        if re.search(r'\d', t):
            sc += 3
        for w in FUNC_WORDS:
            if w in t:
                sc += 2
        if any(b in t for b in BORING):
            sc -= 2
        n = len(re.sub(r'\s', '', t))
        if 12 <= n <= 40:
            sc += 2
        elif n < 8:
            sc -= 3
        return sc

    scored = [(info_score(sg.get('text', '')), sg) for sg in segs]
    scored.sort(key=lambda x: -x[0])

    # ── 2. 换专名 ──
    # 原片里的项目名/工具名要换成目标项目名，否则文案会串
    ORIGINAL_NAMES = re.compile(
        r'Codex|ChatGPT|GPT|HyperFrames|Happy Frames|Remotion|video-use|Videos|'
        r'Seedance|Cdass2|Video Cut|Videocat|Generative Media|'
        r'(?:这个|那个)?(?:skill|skills)|插件|工具包',
        re.I,
    )

    def swap(t):
        # 先纠正 whisper 的误听（冬孝→动画、主秒→分镜…），
        # 再去掉原片专名，避免念出来是错的
        t = fix_text(t or '')
        t = ORIGINAL_NAMES.sub('', t)
        t = re.sub(r'\s+', '', t)
        # 替换后可能粘连出重复词（主秒分镜 → 分镜分镜），去一次
        t = re.sub(r'(.{2,4})\1', r'\1', t)
        return t.strip('，。、；：')

    # ── 3. 组 vo1 ──
    p1 = []

    # 钩子：优先用原片第一句（去掉专名后），否则用数字/卖点造一个
    opener = swap(segs[0].get('text', ''))
    if len(opener) >= 6 and info_score(opener) > -2:
        p1.append(opener.rstrip('？?!！') + '？')
    elif star and star > 10000:
        p1.append(f'{star:,} 星的开源项目，你还没用过？')
    elif head:
        p1.append(f'{head.rstrip("。")}，这个开源项目值得看看。')
    else:
        p1.append('这个开源项目值得看看。')

    # 主体：项目名 + 一句话
    if head:
        p1.append(f'{name}，{head.rstrip("。")}。')
    elif tag:
        p1.append(f'{name}，{tag.rstrip("。")}。')

    # 从原片补句子直到够字数（跳过已经很短的钩子）
    for _sc, sg in scored:
        if sum(cn_len(x) for x in p1) >= cap1 - 20:
            break
        t = swap(sg.get('text', ''))
        if len(t) < 8:
            continue
        # 已经说过的意思不重复
        if any(t[:6] in x for x in p1):
            continue
        p1.append(t + '。')

    # 还不够就上 content.json 的特性
    feats = c.get('features') or []
    titles = [f.get('title') if isinstance(f, dict) else str(f) for f in feats[:3]]
    titles = [t.rstrip('。') for t in titles if t]
    if titles and sum(cn_len(x) for x in p1) < cap1 - 10:
        p1.append('上手就有这些：' + '、'.join(titles) + '。')

    if star and sum(cn_len(x) for x in p1) < cap1 - 10:
        p1.append(f'GitHub 上 {star:,} 个 star，代码全部公开。')

    vo1 = ''.join(p1)[:cap1]

    # ── 4. 组 vo2 ──
    p2 = []
    concl = c.get('conclusion') or []
    if concl:
        p2.append('一句话总结：' + '，'.join(str(x) for x in concl[:3]) + '。')

    # 原片后段的句子（讲怎么用/结论的）
    tail = sorted(segs, key=lambda sg: sg.get('start', 0))[-3:]
    for sg in tail:
        if sum(cn_len(x) for x in p2) >= cap2 - 15:
            break
        t = swap(sg.get('text', ''))
        if len(t) >= 8 and not any(t[:6] in x for x in p2):
            p2.append(t + '。')

    if sum(cn_len(x) for x in p2) < cap2 - 10:
        p2.append(f'仓库搜 {name}，装好就能用。')

    vo2 = ''.join(p2)[:cap2]

    return {'vo1': vo1, 'vo2': vo2}


def main():
    proj = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('.').resolve()
    content_path = proj / 'content.json'
    if not content_path.exists():
        sys.exit(f'没有 {content_path}')

    c = json.loads(content_path.read_text(encoding='utf-8'))
    asr_path = arg('--from-asr')
    style = arg('--style', 'template')
    tpl_style = arg('--tpl-style')      # 视频风格，决定文案骨架

    variants = {}

    tpl = template_script(c)
    variants['template'] = tpl

    # 风格化文案：四条片子同一个项目，文案必须不同，
    # 否则音频指纹一样，平台判重复内容
    if tpl_style:
        styled = styled_script(c, tpl_style)
        if styled:
            variants['styled'] = styled

    if asr_path and Path(asr_path).exists():
        asr = json.loads(Path(asr_path).read_text(encoding='utf-8'))
        ref = reference_script(c, asr)
        if ref:
            variants['reference'] = ref

    # 选一档写进 vo1/vo2
    pick = style if style in variants else 'template'
    chosen = variants[pick]

    copy = {
        'voice': 'zh-CN-YunxiNeural', 'rate': '+45%', 'pitch': '+5Hz',
        'vo1_at': 0.6, 'vo2_at': 21.1,
        'vo1': chosen['vo1'],
        'vo2': chosen['vo2'],
        'variants': variants,
        'chosen': pick,
        '_note': '改 vo1/vo2 直接生效；variants 里保留了两档供对比',
    }

    out = proj / 'audio' / 'copy.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(copy, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'✓ {out}')
    print(f'  采用：{pick}')
    print()
    for k, v in variants.items():
        print(f'── {k}  (vo1 {cn_len(v["vo1"])} 字 / vo2 {cn_len(v["vo2"])} 字)')
        print(f'   {v["vo1"]}')
        print(f'   {v["vo2"]}')
        print()


if __name__ == '__main__':
    main()
