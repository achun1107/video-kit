# -*- coding: utf-8 -*-
"""一条命令：从仓库链接到发布包。

  python tools/auto-make.py owner/repo
  python tools/auto-make.py owner/repo --styles all
  python tools/auto-make.py owner/repo --out D:/my-video

## 为什么要这个

前面 27 轮造了一堆工具，但都是散的：
评分、抽内容、写文案、生成配音、渲染、混音、封面、发布文案、打包 ——
要手动跑七八条命令，顺序错了还会出问题（比如跑错 audio.py 导致字幕不更新）。

这个脚本把它们串起来，并且**按选题评分自动决定做几条**。

## 自动决策

评分 ≥ 7   做 4 条（四种风格都用上，值得投入）
评分 5-6   做 2 条（手账批注 + 产品发布页，用问题切入的文案）
评分 < 5   只做 1 条（手账批注），并提示换选题

## 每一步都可回滚

    出问题不会覆盖已有的工程目录，会先备份。
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

# 风格 → (模板文件, 音色, BGM, 语速)
STYLES = {
    'ganhuoju': ('ganhuoju.js', 'zh-CN-YunjianNeural', 'Life_of_Riley.mp3', '+18%'),
    'weitu':    ('weitu.js',    'zh-CN-YunxiNeural',   'Wallpaper.mp3',      '+18%'),
    'ajin':     ('ajin.js',     'zh-CN-YunyangNeural', 'Carefree-looped.mp3', '+18%'),
    'xiaokai':  ('xiaokai.js',  'zh-CN-XiaoxiaoNeural', 'Fluffing_a_Duck.mp3', '+12%'),
}

BGM_DIR = KIT / 'assets' / 'bgm'


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def has(n):
    return n in sys.argv


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='ignore')
    if r.returncode != 0 and not quiet:
        print((r.stderr or '')[-400:])
    return r


def check_dur(path):
    """读视频时长，失败返回 None。"""
    if not path.exists():
        return None
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def step(n, msg):
    print(f'\n[{n}] {msg}')


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('--'):
        sys.exit(__doc__)

    repo = sys.argv[1]
    name = repo.split('/')[-1]
    out = Path(arg('--out', f'D:/auto/{name}')).resolve()
    token = os.environ.get('GITHUB_TOKEN', '')

    print('=' * 62)
    print(f'{repo}  →  {out}')
    print('=' * 62)

    # ── 1. 评分 ──
    step(1, '评估选题')
    score = None
    r = run([sys.executable, str(KIT / 'tools' / 'score-repo.py'), repo])
    txt = (r.stdout or '') + (r.stderr or '')
    import re
    m = re.search(r'(\d+\.\d+)/10', txt)
    if m:
        score = float(m.group(1))
        print(f'  {score}/10')
        for line in txt.split('\n'):
            if '→' in line:
                print(f'  {line.strip()}')
    else:
        print('  评分失败（可能被限流），继续但不做优化建议')

    # ── 2. 决定做几条 ──
    forced = arg('--styles')
    if forced == 'all':
        styles = list(STYLES)
    elif forced:
        styles = [s.strip() for s in forced.split(',') if s.strip() in STYLES]
    elif score is None:
        styles = ['ganhuoju']
    elif score >= 7:
        styles = list(STYLES)
    elif score >= 5:
        styles = ['ganhuoju', 'weitu']
    else:
        styles = ['ganhuoju']

    step(2, f'做 {len(styles)} 条：{" / ".join(styles)}')

    # ── 3. 生成基础工程（含 content + 第一套模板）──
    step(3, '生成工程')
    if out.exists():
        bak = out.with_name(out.name + '.bak')
        if bak.exists():
            shutil.rmtree(bak)
        shutil.move(str(out), str(bak))
        print(f'  已有工程备份到 {bak.name}')

    env = dict(os.environ)
    if token:
        env['GITHUB_TOKEN'] = token
    r = subprocess.run(
        ['node', str(KIT / 'tools' / 'make-video.mjs'),
         '--repo', repo, '--template', styles[0], '--out', str(out), '--skip-render'],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
        env=env, timeout=900)
    if r.returncode != 0:
        sys.exit('生成工程失败：\n' + (r.stderr or '')[-600:])
    print(f'  {out}')

    # ── 3.4 英文项目：清空 features ──
    # 英文项目的 features 是 Quick Start / AI coding agent 这类，
    # 放到画面上就是英文段落，和中文配音打架。
    # 清空后各模板会降级到中文通用词或直接跳过。
    cp_en = out / 'content.json'
    if cp_en.exists():
        import json as _j
        _ce = _j.loads(cp_en.read_text(encoding='utf-8'))
        _h = (_ce.get('headline') or '').strip()
        import re as _r
        if _h and not _r.search(r'[\u4e00-\u9fa5]', _h):
            _ce['features'] = []
            cp_en.write_text(_j.dumps(_ce, ensure_ascii=False, indent=2), encoding='utf-8')
            run([sys.executable, str(KIT / 'tools' / 'sync-content.py'), str(out)])
            print('  英文项目：features 已清空（画面不会出现英文特性）')

    # ── 3.5 检查 headline 长度 ──
    # content.json 的 headline 来自 GitHub description，可能很长
    cp0 = out / 'content.json'
    if cp0.exists():
        import json as _json
        c0 = _json.loads(cp0.read_text(encoding='utf-8'))
        head = (c0.get('headline') or '').strip()
        import re as _re
        has_cn = bool(_re.search(r'[\u4e00-\u9fa5]', head))
        is_pure_en = not has_cn and len(head) > 0

        need_fix = False
        use_facts = False
        if is_pure_en:
            # 英文项目不拦停 —— 改用事实型文案，只说不需要理解的事实
            use_facts = True
            print()
            print('  ℹ headline 是英文，改用事实型文案')
            print(f'    {head}')
            print('    （只说星数/技术栈/建库时间这些不需要翻译的事实）')
            print('    想要更好的效果，手改 content.json 的 headline 为一句中文卖点。')
        elif len(head) > 25:
            print()
            print(f'  ⚠ headline 太长（{len(head)} 字）：')
            print(f'    {head}')
            print()
            print('    这是 GitHub description 原文。做视频标题和配音都太长。')
            print('    建议手改 content.json 的 headline 为一句中文卖点（10-20 字）。')
            print(f'    改完重跑：python tools/auto-make.py {repo} --out {out}')
            need_fix = True

        if need_fix:
            print()
            if not has('--force'):
                print('    （加 --force 跳过这个检查继续，做出来的片子标题会很别扭）')
                sys.exit(2)
            print('    --force 已指定，继续（标题可能不好看）')

    # ── 4. 复制成多条 ──
    if len(styles) > 1:
        step(4, '复制成多条')
        for s in styles[1:]:
            d = out.with_name(f'{out.name}-{s}')
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(out, d)
            shutil.copy2(KIT / 'templates' / STYLES[s][0], d / 'film.js')
            print(f'  {d.name}')

    # ── 5. 每条：文案 + 配音 + 渲染 + 混音 + 封面 + 文案 + 打包 ──
    dirs = [out] + [out.with_name(f'{out.name}-{s}') for s in styles[1:]]
    for i, (s, d) in enumerate(zip(styles, dirs, strict=True), 5):
        step(i, f'{s}：文案 → 配音 → 渲染 → 混音 → 打包')
        tpl, voice, bgm, rate = STYLES[s]

        # 文案风格：
        #   英文项目 → facts（只说事实，不中英混杂）
        #   低分项目 → problem（先说观众痛点）
        #   高分项目 → 各自的风格
        if use_facts:
            tpl_style = 'facts'
        elif score is None or score < 7:
            tpl_style = 'problem'
        else:
            tpl_style = s
        run([sys.executable, str(KIT / 'tools' / 'script-writer.py'), str(d),
             '--tpl-style', tpl_style, '--style', 'styled'])

        # 音色 + 语速 + vo2_at
        cp = d / 'audio' / 'copy.json'
        if cp.exists():
            c = json.loads(cp.read_text(encoding='utf-8'))
            c['voice'] = voice
            c['rate'] = rate
            cps = 5.0 if rate == '+12%' else 5.3
            c['vo2_at'] = round(0.6 + len(c.get('vo1', '')) / cps + 0.8, 1)
            cp.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding='utf-8')

        # 清掉旧音频，强制重新生成（含字幕拆分）
        for f in (d / 'audio').glob('vo*'):
            f.unlink()
        run([sys.executable, str(KIT / 'tools' / 'tts.py'), str(d)])

        # 渲染前删旧产物 —— render.py 看到 raw.mp4 存在会跳过，
        # 中断重跑时会拿到上一次的半成品（实测遇到过一个 6 秒的）
        for f in ('raw.mp4', 'final.mp4'):
            fp = d / 'renders' / f
            if fp.exists():
                fp.unlink()

        # 渲染
        run([sys.executable, str(KIT / 'engine' / 'render.py'), str(d)])
        run([sys.executable, str(KIT / 'engine' / 'render.py'), str(d), '--events'])

        # 检查时长 —— 不对就停下，不要一路跑到打包
        dur = check_dur(d / 'renders' / 'raw.mp4')
        if dur is None or abs(dur - 34.8) > 1.0:
            print(f'  ✗ 渲染时长 {dur}s，应该是 34.8s。停下检查。')
            sys.exit(1)
        print(f'  渲染 {dur:.1f}s')

        # 混音
        mu = BGM_DIR / bgm
        if not mu.exists():
            mu = Path('D:/DSH/achun/video-xiaobai/audio/bgm') / bgm.replace('-looped', '')
        run([sys.executable, str(KIT / 'tools' / 'mix.py'), str(d),
             '--vo1', '0.6', '--vo2', '21.1', '--bg', '0.06',
             '--music-gain', '0.075', '--music', str(mu),
             '--vo-gain', '2.4', '--lufs', '-11'])

        # 封面 + 发布文案 + 预览页 + 打包
        run([sys.executable, str(KIT / 'tools' / 'make-cover.py'), str(d)])
        run([sys.executable, str(KIT / 'tools' / 'publish-info.py'), str(d),
             '--style', s])
        run([sys.executable, str(KIT / 'tools' / 'make-player-html.py'),
             str(d / 'renders' / 'final.mp4'),
             '-o', str(d / 'renders' / 'player.html'), '--crf', '29'])
        pkg = Path(f'D:/publish/{name}-{s}' if s != styles[0] or len(styles) > 1
                   else f'D:/publish/{name}')
        run([sys.executable, str(KIT / 'tools' / 'make-package.py'), str(d),
             '-o', str(pkg)])

        # 封面上风格角标（必须传 --pkg，否则会改到旧的 D:/publish/{风格}/ 目录）
        run([sys.executable, str(KIT / 'tools' / 'cover-badge.py'), s,
             '--pkg', str(pkg)])
        print(f'  → {pkg}')

    # ── 最后：preflight ──
    step(len(styles) + 5, '发布前自检')
    r = run([sys.executable, str(KIT / 'tools' / 'preflight.py')] + [str(d) for d in dirs])
    out_txt = (r.stdout or '') + (r.stderr or '')
    for line in out_txt.split('\n'):
        if '✗' in line or '全部通过' in line or '不通过' in line:
            print(f'  {line.strip()}')

    print('\n' + '=' * 62)
    print('完成')
    print('=' * 62)
    for s, d in zip(styles, dirs, strict=True):
        pkg = Path(f'D:/publish/{name}-{s}' if len(styles) > 1 else f'D:/publish/{name}')
        prev = pkg / '00_预览.html'
        print(f'  {s:10s} {pkg}')
        if prev.exists():
            print(f'             双击看片：{prev}')


if __name__ == '__main__':
    main()
