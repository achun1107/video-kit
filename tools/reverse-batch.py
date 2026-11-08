# -*- coding: utf-8 -*-
"""批量逆向抖音视频：下载 → 转写 → 找仓库，按点赞排序。

  python tools/reverse-batch.py rank.json -o reversed.json --top 5
  python tools/reverse-batch.py rank.json --top 21 --model small

对每条视频产出：
  digg / title / 转写字数 / 语速 / 找到的仓库 / 提到的工具名

找仓库的三层策略（命中即停）：
  1. 转写文本里的 github.com/owner/repo
  2. 已知工具名映射（含转写误听变体）
  3. 文本里的 owner/repo 形态 + 标题里的 GitHub 关键词
"""
import sys, json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE
DL = Path('douyin/dl')
ASR = Path('douyin/asr')


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


# 已知工具 → 仓库（含 whisper 常见误听）
KNOWN = [
    # 视频 / 渲染
    (['hyperframes', 'hyper frames', 'happy frames', 'hyperframe'], 'heygen-com/hyperframes'),
    (['video-use', 'video use', 'videouse', 'videos use'], 'browser-use/video-use'),
    (['remotion'], 'remotion-dev/remotion'),
    (['openfilm', 'open film'], ''),
    (['seedance'], ''),
    # 爬虫 / 数据
    (['crawl4ai', 'crawler4ai', 'crawl4 ai'], 'unclecode/crawl4ai'),
    (['firecrawl', 'fire crawl'], 'mendableai/firecrawl'),
    # UI / 设计
    (['shadcn', 'shad cn'], 'shadcn-ui/ui'),
    (['tailwind'], 'tailwindlabs/tailwindcss'),
    # 插件 / 工具
    (['purrge', 'purge'], ''),
    (['rakazo', 'rakaso'], ''),
    (['headroom', 'headropm', 'head room'], ''),
    # 教程
    (['happy-llm', 'happyllm'], 'datawhalechina/happy-llm'),
    (['datawhale'], 'datawhalechina'),
]

RE_REPO = [
    r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',
    r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*(?:这个|的)?\s*(?:仓库|项目|repo|skill)',
    r'(?:仓库|项目|repo|skill)\s*(?:叫|是|：|:)?\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',
]


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if r.returncode != 0 and not quiet:
        print(r.stderr[-400:])
    return r


def transcribe(mp4, asr_json, model='small'):
    if asr_json.exists():
        try:
            return json.loads(asr_json.read_text(encoding='utf-8'))
        except Exception:
            pass
    run(['python', str(TOOLS / 'transcribe-local.py'), str(mp4),
         '--model', model, '--out', str(asr_json)], quiet=False)
    try:
        return json.loads(asr_json.read_text(encoding='utf-8'))
    except Exception:
        return {'full': '', 'repos': [], 'chars': 0, 'duration': 0, 'rate': 0}


def find_repo(title, full):
    low_t, low_b = title.lower(), full.lower()

    # 1. 文本里直接写的 github.com/owner/repo
    for m in re.finditer(RE_REPO[0], full, re.I):
        r = m.group(1).strip('/.')
        if r and '/' in r:
            return r, 'text:github.com'

    # 2. 已知工具名（标题优先）
    for src, tag in ((low_t, 'title'), (low_b, 'text')):
        for needles, slug in KNOWN:
            if not slug:
                continue
            for n in needles:
                if n in src:
                    return slug, f'{tag}:{n}'

    # 3. 通用的 owner/repo 形态
    for pat in RE_REPO[1:]:
        for m in re.finditer(pat, full, re.I):
            r = m.group(1).strip('/.')
            if '/' in r and not r.lower().startswith(('http', 'www')) and len(r) < 60:
                return r, 'text:pattern'

    return None, None


def tool_names(full):
    """从文本里捞可能的英文工具名，给没找到仓库的视频留线索。"""
    names = re.findall(r'[A-Za-z][A-Za-z0-9_\-]{2,}', full)
    skip = {'the', 'and', 'for', 'you', 'with', 'this', 'that', 'can', 'not', 'are',
            'codex', 'gpt', 'ai', 'skill', 'skills', 'github', 'openai', 'claude'}
    seen, out = set(), []
    for n in names:
        k = n.lower()
        if k in skip or k in seen:
            continue
        seen.add(k)
        out.append(n)
    return out[:10]


def main():
    rank_path = sys.argv[1] if len(sys.argv) > 1 else 'rank.json'
    top = int(arg('--top', '5'))
    model = arg('--model', 'small')
    out_path = arg('-o', 'reversed.json')

    rank = json.loads(Path(rank_path).read_text(encoding='utf-8'))
    vids = rank['videos'][:top]
    print(f'共 {rank["count"]} 条，逆向前 {len(vids)} 条（按点赞）\n')

    DL.mkdir(parents=True, exist_ok=True)
    ASR.mkdir(parents=True, exist_ok=True)

    results = []
    for i, v in enumerate(vids, 1):
        vid = v['id']
        print(f'── {i}/{len(vids)}  {v["digg"]:,} 赞  {v["title"][:40]}')

        mp4 = DL / f'{vid}.mp4'
        if not mp4.exists():
            r = run(['python', str(TOOLS / 'douyin-download.py'), vid, '-o', str(DL)],
                    quiet=False)
            if not mp4.exists():
                print('   ✗ 下载失败')
                results.append({**v, 'ok': False, 'reason': 'download_failed'})
                continue

        asr = transcribe(mp4, ASR / f'{vid}.json', model)
        full = asr.get('full', '')
        repo, how = find_repo(v['title'], full)

        print(f'   {asr.get("chars",0)} 字 / {asr.get("duration",0)}s = {asr.get("rate",0)} 字/秒')
        if repo:
            print(f'   ✓ 仓库 {repo}  （{how}）')
        else:
            print(f'   · 没找到仓库；工具名: {", ".join(tool_names(full)[:6])}')

        results.append({
            **v,
            'ok': True,
            'chars': asr.get('chars', 0),
            'duration': asr.get('duration', 0),
            'rate': asr.get('rate', 0),
            'repo': repo,
            'repo_how': how,
            'tools': tool_names(full),
            'full': full,
        })

    found = [r for r in results if r.get('repo')]
    print(f'\n{"="*56}')
    print(f'完成 {len(results)} 条，找到仓库 {len(found)} 个')
    for r in found:
        print(f'  {r["digg"]:>8,} 赞  {r["repo"]:38s} {r["title"][:26]}')

    Path(out_path).write_text(json.dumps({'rank': rank_path, 'items': results},
                                         ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n写到 {out_path}')


if __name__ == '__main__':
    main()
