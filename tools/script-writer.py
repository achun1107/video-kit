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
import sys, json, re
from pathlib import Path


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def clean(s):
    return re.sub(r'\s+', '', s or '')


def cn_len(s):
    return len(clean(s))


# ────────────────────────── 模板稿 ──────────────────────────

HOOKS = [
    '还在手动做视频吗？',
    '这个开源项目，值得花两分钟看看。',
    '如果你也在用 AI 干活，这个别错过。',
    '又发现一个能省时间的东西。',
]

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
    """借原片的节奏，换主语。

    原片转写是按句切好的（segments），我们把前半段（讲"是什么"）
    映射到 vo1，后半段（讲"怎么用/结论"）映射到 vo2。
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

    # 原片的总时长和语速
    total = segs[-1].get('end', 0) or 0
    chars = asr.get('chars') or cn_len(full)
    rate = asr.get('rate') or (chars / max(total, .1))

    # 原片前 3 句的句式，用来起头（保留节奏感，去掉具体名词）
    opener = segs[0].get('text', '') if segs else ''
    opener = re.sub(r'Codex|GPT|Skill|skills|AI', '', opener, flags=re.I).strip('，。 ')

    p1 = []
    if opener and len(opener) > 4:
        p1.append(opener.rstrip('，。') + '？')
    else:
        p1.append('这个开源项目值得看看。')

    if head:
        p1.append(f'{name}，{head.rstrip("。")}。')
    elif tag:
        p1.append(f'{name}，{tag.rstrip("。")}。')

    feats = c.get('features') or []
    titles = []
    for f in feats[:3]:
        t = f.get('title') if isinstance(f, dict) else str(f)
        if t:
            titles.append(t.rstrip('。'))
    if titles:
        p1.append('上手就有这些：' + '、'.join(titles) + '。')

    if star:
        p1.append(f'{star:,} 个 star，全部开源。')

    cap = int(rate * 20)   # vo1 目标 20 秒
    vo1 = ''.join(p1)[:cap]

    p2 = []
    concl = c.get('conclusion') or []
    if concl:
        p2.append('一句话总结：' + '，'.join(str(x) for x in concl[:3]) + '。')
    p2.append(f'仓库搜 {name}，装好就能用。')
    vo2 = ''.join(p2)[:int(rate * 11)]

    return {'vo1': vo1, 'vo2': vo2}


def main():
    proj = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path('.').resolve()
    content_path = proj / 'content.json'
    if not content_path.exists():
        sys.exit(f'没有 {content_path}')

    c = json.loads(content_path.read_text(encoding='utf-8'))
    asr_path = arg('--from-asr')
    style = arg('--style', 'template')

    variants = {}

    tpl = template_script(c)
    variants['template'] = tpl

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
