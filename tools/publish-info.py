# -*- coding: utf-8 -*-
"""生成各平台的发布信息：标题、话题、简介。

发布不是"传个视频就完了"。同一个片子，四个平台要写四套文案：

  抖音     标题短（20 字内）+ 钩子 + emoji，话题 3-5 个
  小红书   标题长（20 字，可带表情）+ 种草语气，话题 5-8 个，正文分段
  视频号   标题稳（不加 emoji），话题 2-3 个
  B站      标题可长，技术向，标签走 tag 系统

  python tools/publish-info.py <工程目录>
  python tools/publish-info.py <工程目录> --style ganhuoju

产出 <工程>/renders/publish.md 和 publish.json

## 标题怎么来

不用 AI 生成 —— 用 content.json 里的 namePlain / headline / star 拼，
再套每个平台的话术模板。这样可控，不会出现"AI 瞎编"。
"""
import json
import re
import sys
from pathlib import Path

# 各平台的话术模板
TEMPLATES = {
    'douyin': {
        'title': '{hook}｜{name}',
        'hook_pool': [
            '{star} 星的冷门开源项目',
            'github 上又火了',
            '不用注册不用订阅',
            '这个开源项目有点东西',
        ],
        'tags': ['#github', '#开源', '#AI编程', '#程序员', '#效率工具', '#技术分享'],
        'max_tags': 5,
        'intro_style': 'short',
    },
    'xhs': {
        'title': '发现一个宝藏开源项目！{name}｜{headline}',
        'tags': ['#开源项目', '#github', '#程序员', '#AI工具', '#效率提升',
                 '#自学编程', '#副业', '#科技'],
        'max_tags': 8,
        'intro_style': 'seed',
    },
    'channels': {
        'title': '{name}：{headline}',
        'tags': ['#开源', '#程序员', '#AI'],
        'max_tags': 3,
        'intro_style': 'plain',
    },
    'bilibili': {
        'title': '【开源推荐】{name} - {headline}（{star}★）',
        'tags': ['开源', 'GitHub', '程序员', 'AI', '效率工具'],
        'max_tags': 5,
        'intro_style': 'tech',
    },
}


# 各风格的抖音钩子池（同一项目发多条时，标题必须不同）
STYLE_HOOKS = {
    # 每条标题都按对标账号的爆款公式写：
    #   [对比问句] + [项目名] + [具体产出]
    # 爆款 Top15 里 10 条点了具体工具名，模糊说法（"一个工具"）几乎不出爆款。
    'ajin': [
        'AI 编程教程看了十套还是懵？{name} 直接上手演示',
        '录屏走一遍 {name}，只说话就出活',
        '{name} 怎么用？三分钟看完你能上手',
    ],
    'ganhuoju': [
        # 不拿 star 数当卖点 —— 133 星这个量级反而暴露弱点。
        # 用「对比问句 + 具体产出」打开，和爆款 Top15 的写法一致。
        'AI 编程看了十套还是懵？{name} 只说话就出活',
        '{name} 能干的事，比你想的多',
        '先给结论：{name} 这三件事最值钱',
    ],
    'xiaokai': [
        '{name} 值不值得试？我把它拆成三块看',
        '又挖到一个宝藏？{name} 到底香在哪',
        '{star} 星的小众项目 {name}，三个点说清',
    ],
    'weitu': [
        '{name} 刚开源：只说话就出活，{star} 星',
        '{name} 发布页：三个能力一次看完',
        '开源新项目 {name}，{star} 星什么水平',
    ],
    'problem': [
        'AI 编程看了十套还是懵？{name} 换个思路',
        '一上手就卡住？{name} 把门槛全拆了',
        '不会写代码能用 AI 吗？{name} 试试',
    ],
    'facts': [
        '{name}：{star} 星的 {lang} 项目，值不值得看',
        '{star} 星 {lang} 项目 {name}，数据说话',
        '{name} 是什么？{star} 星，{lang} 写的',
    ],
}

# 各风格的封面标题（比视频标题更短，缩略图上要能看清）
STYLE_COVER = {
    'ajin': '带你看',
    'ganhuoju': '划重点',
    'xiaokai': '挖到了',
    'weitu': '刚开源',
}


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


# 受众句式：这些是「适合谁」，不是「有什么功能」，不能当卖点写
AUDIENCE_RE = re.compile(
    r'^(给|适合|面向|针对).*(的人|用户|同学|小白|新手)$'
    r'|^(给|适合|面向)'          # 「给真人（小白）」这种带括号的
    r'|^(想|想要|准备).*(的|人)'
)


# 功能动词：真功能点几乎都带这些，纯名词短语（分类名）不会
FUNC_VERB_RE = re.compile(
    r'支持|可以|能够|自动|一键|生成|内置|集成|导出|导入|同步|识别|'
    r'转换|部署|调试|检索|抓取|解析|渲染|编排|托管|分发|接入|适配|'
    r'可视化|批处理|实时|离线|多语言|跨平台|零配置|开箱'
)


def clean_features(c, limit=3):
    """抽出真正的功能点。

    两道闸：
      1. 排除受众句式（「给真人（小白）」）
      2. 必须有功能动词 —— 纯名词短语是分类名，不是功能
    """
    out = []
    for f in (c.get('features') or []):
        t = f.get('title') if isinstance(f, dict) else str(f)
        t = str(t or '').strip()
        if not t or len(t) < 4:
            continue
        if AUDIENCE_RE.search(t):
            continue
        if not FUNC_VERB_RE.search(t):
            continue       # 「出图与创作」这种名词短语，跳过
        out.append(t)
        if len(out) >= limit:
            break
    return out


def intro(style, c):
    name = c.get('namePlain') or c.get('name') or '这个项目'
    head = (c.get('headline') or '').strip()
    star = (c.get('stats') or {}).get('star')
    feats = clean_features(c)

    star_s = f'{star:,} star' if star else '完全开源'

    if style == 'short':
        return f'{head}。{star_s}，代码全公开。'

    if style == 'seed':
        lines = [f'最近挖到一个开源项目，叫 {name}。']
        if head:
            lines.append(f'它的核心是：{head}。')
        if feats:
            lines.append('几个我觉得实用的点：')
            for f in feats:
                lines.append(f'· {f}')
        # 抽不到真功能点就直接到 star 段（不写废话兜底）
        lines.append(f'目前 {star_s}，完全免费，不用注册。')
        lines.append('适合想学 AI 编程但不知道从哪下手的人。')
        return '\n'.join(lines)

    if style == 'plain':
        return f'{name}，{head}。{star_s}，开源免费。'

    # tech
    lines = [f'{head}。']
    if feats:
        lines.append('主要特性：')
        for f in feats:
            lines.append(f'- {f}')
    lines.append(f'GitHub: {c.get("owner", "")}/{c.get("repo", "")}（{star_s}）')
    return '\n'.join(lines)


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    cp = proj / 'content.json'
    if not cp.exists():
        sys.exit(f'没有 {cp}')
    c = json.loads(cp.read_text(encoding='utf-8'))

    name = c.get('namePlain') or c.get('name') or '项目'
    head = (c.get('headline') or '').strip()
    star = (c.get('stats') or {}).get('star')

    style = arg('--style')
    style_hooks = STYLE_HOOKS.get(style) if style else None

    out = {}
    for plat, tpl in TEMPLATES.items():
        title = tpl['title'].format(
            name=name,
            headline=head[:16],
            hook=(style_hooks[0] if style_hooks
                  else tpl.get('hook_pool', ['值得看看'])[0]).format(
                star=f'{star:,}' if star else '过万', name=name),
            star=f'{star:,}' if star else '开源',
        )
        tags = tpl['tags'][:tpl['max_tags']]
        out[plat] = {
            'title': title,
            'tags': tags,
            'intro': intro(tpl['intro_style'], c),
        }

    # 写 JSON
    jp = proj / 'renders' / 'publish.json'
    jp.parent.mkdir(exist_ok=True)
    jp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    # 写 Markdown（给人看，方便复制粘贴）
    md = ['# 发布信息', '', f'项目：{name}　{star:,} star' if star
          else f'项目：{name}', '']

    LABEL = {'douyin': '抖音', 'xhs': '小红书',
             'channels': '视频号', 'bilibili': 'B站'}

    for plat, info in out.items():
        md.append(f'## {LABEL[plat]}')
        md.append('')
        md.append('**标题**')
        md.append('```')
        md.append(info['title'])
        md.append('```')
        md.append('')
        md.append('**话题**')
        md.append('```')
        md.append(' '.join(info['tags']))
        md.append('```')
        md.append('')
        md.append('**简介**')
        md.append('```')
        md.append(info['intro'])
        md.append('```')
        md.append('')
        md.append('**封面**：`renders/cover-' + plat + '.png`')
        md.append('')
        md.append('---')
        md.append('')

    mp = proj / 'renders' / 'publish.md'
    mp.write_text('\n'.join(md), encoding='utf-8')

    print(f'{mp}')
    print(f'{jp}')
    print()
    for plat, info in out.items():
        print(f'── {LABEL[plat]}')
        print(f'   标题：{info["title"]}')
        print(f'   话题：{" ".join(info["tags"][:4])}')


if __name__ == '__main__':
    main()
