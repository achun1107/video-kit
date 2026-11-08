# -*- coding: utf-8 -*-
"""whisper 转写的中文误听纠正表 + 关键词清洗。

实测 5 条抖音视频，whisper small 的误听有规律：
  英文专名几乎必错，中文专名错在近音字，数字偶尔错。

  python tools/asr-fix.py <文本>        # 直接看纠正效果
  被 repo-finder.py / reverse-batch.py import
"""

import re

# ────────────── 专名误听 → 正确写法 ──────────────
# key 用小写，匹配时也转小写
NAME_FIX = {
    # 工具 / 产品
    'chess cpt': 'ChatGPT',
    'chess gpt': 'ChatGPT',
    'chat cpt': 'ChatGPT',
    'checks gpt': 'ChatGPT',
    'codes': 'Codex',           # 注意：只在"给 CodeS 配上"这类语境下对，但总体利大于弊
    'code x': 'Codex',
    'codex': 'Codex',
    'gatehub': 'GitHub',
    'git hub': 'GitHub',
    'gitlib': 'GitHub',
    'happy frames': 'HyperFrames',
    'hyper frames': 'HyperFrames',
    'hyperframe': 'HyperFrames',
    'videocat': 'Video Cut',
    'video cat': 'Video Cut',
    'cdass2': 'Seedance',
    'see dance': 'Seedance',
    'seedance': 'Seedance',
    'generative media': 'Generative Media',
    'remotion': 'Remotion',
    'openfilm': 'OpenFilm',
    'open film': 'OpenFilm',
    'rakazo': 'Rakazo',
    'rakaso': 'Rakazo',
    'purrge': 'purrge',
    'headropm': 'Headroom',
    'headroom': 'Headroom',
    'tars': 'UI-TARS',
    'ui tars': 'UI-TARS',
    'agent lightning': 'Agent Lightning',
    'microsoft': 'Microsoft',
    'mcp': 'MCP',

    # 公司 / 品牌
    '温软': '微软',
    '字节跳动': '字节跳动',
    '豆包': '豆包',

    # 中文专名
    '紫围斗树': '紫微斗数',
    '紫薇斗数': '紫微斗数',
    '紫微斗术': '紫微斗数',
    '命盘': '命盘',
    '排盘': '排盘',

    # 通用词
    '冬孝': '动画',
    '动效': '动效',
    '主秒': '分镜',
    '分镜': '分镜',
    '一战士': '一站式',
    '一站事': '一站式',
    '接惯': '接管',
    '较证': '校正',
    '校对': '校对',
    '狂懒': '斩获',
    '悬学': '玄学',
    '面像': '面向',
    '面相': '面向',
    '面相智能体': '面向智能体',
    '一流烂气': '（略）',
    '触手': '触手',
    '语数': '语速',
    'tokens': 'Token',
    'token': 'Token',
}

# 这些词不该进关键词（虚词 / 高频词）
STOP_WORDS = set('''
这个 那个 一个 什么 可以 就是 不是 还有 然后 所以 但是 因为 如果 虽然
已经 能够 支持 使用 起来 进去 出来 时候 东西 一起 一样 非常 特别 真的
确实 比较 功能 项目 开源 框架 工具 直接 自动 全部 完全 免费 大家 我们
你们 他们 现在 知道 这里 那里 这样 那样 怎么 为什么 多少 需要 只要 就能
之后 之前 之前 下来 上来 过了 的话 的是 了的 了的 一下 一点 一些 这个项目
'''.split())


def fix_text(s):
    """纠正误听，返回新字符串。

    必须一次性替换（所有 key 合成一个 alternation）。
    循环 replace 会出事：'hyperframe' 会把上一步刚替换出的 'HyperFrames'
    再吃一次，变成 'HyperFramess'。
    """
    if not s:
        return s
    keys = sorted(NAME_FIX, key=len, reverse=True)
    pattern = '|'.join(re.escape(k) for k in keys)

    def repl(m):
        return NAME_FIX.get(m.group(0).lower(), m.group(0))

    return re.sub(pattern, repl, s, flags=re.I)


def clean_keywords(kws):
    """洗掉虚词、单字、纯标点。"""
    out = []
    for k in kws:
        k = k.strip('，。！？、；：""''（）()【】[]得的地')
        if not k or len(k) < 2:
            continue
        if k in STOP_WORDS:
            continue
        if k.lower() in STOP_WORDS:
            continue
        # 全是标点或全是虚词组合
        if all(c in '的了是在和与及或等' for c in k):
            continue
        out.append(k)
    return out


if __name__ == '__main__':
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else '在Gatehub狂懒1.05万star，紫围斗树这个项目，给CodeS配上，温软开源'
    print('原文:', txt)
    print('纠正:', fix_text(txt))
