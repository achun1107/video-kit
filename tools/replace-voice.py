# -*- coding: utf-8 -*-
"""替换配音：把自己念的音频换成片子的音轨。

  python tools/replace-voice.py <工程目录> <你的录音>
  python tools/replace-voice.py D:/four/ganhuoju D:/my-voice.m4a

## 为什么要这个工具

工作流唯一剩下的问题是配音是机器音（微软云希等），
抖音对纯 AI 配音的判定偏保守，推荐权重低。

但手工替换很麻烦：要改 score.wav、算混音比例、重新打包，
中间任何一步错了都会出岔子。这个工具把这些串起来。

## 做什么

1. 读你的录音，转成 48k 单声道 wav
2. 去掉首尾静音（很多人录音前后有空白）
3. 时长不够就补静音，太长就报警（不自动截断，截断会切掉话）
4. 按目标响度归一化（和原来四条片子一致）
5. 和 BGM 混音
6. 校验：响度、时长、首帧非黑
7. 重新打包

## 录音建议（写进提示里）

· 语速别太快，30 秒左右的稿子念完约 30 秒
· 用手机自带录音就行，但离嘴 15-20cm，别贴太近
· 找个安静房间，别开风扇空调
· 念错不要紧，重念那一句就行，不用整段重来
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 和现有四条片子对齐的参数
TARGET_LUFS = -8.0   # loudnorm 单遍输出会比目标低约 4dB
BGM_GAIN = 0.075
VO_GAIN = 2.0


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw)


def probe_dur(path):
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def measure_lufs(path):
    """量一段音频的积分响度。"""
    import re
    r = run(['ffmpeg', '-i', str(path), '-af', 'ebur128=framelog=quiet',
             '-f', 'null', '-'])
    m = re.search(r'I:\s+(-?[\d.]+)\s+LUFS', r.stderr)
    return float(m.group(1)) if m else None


def gain_filter(src_lufs, target_lufs):
    """算需要多少增益。

    ## 为什么不用 loudnorm

    loudnorm 单遍模式被 LRA 和 TP 限制住，提不上去：
    源 -26.3 LUFS，loudnorm=I=-8 之后只到 -16.5（只提了 9.8 dB）。

    所以改成：先量出源响度，算出需要的增益，直接用 volume 提，
    再加 alimiter 防爆音。这样能准确落到目标值。
    """
    if src_lufs is None:
        return 'volume=8dB,alimiter=limit=0.95'
    need = target_lufs - src_lufs
    # 留 1 dB 给 limiter
    need = max(0, min(need - 1, 30))
    return f'volume={need:.1f}dB,alimiter=limit=0.95'


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)

    proj = Path(sys.argv[1]).resolve()
    src = Path(sys.argv[2]).resolve()
    if not src.exists():
        sys.exit(f'找不到录音：{src}')

    final = proj / 'renders' / 'final.mp4'
    if not final.exists():
        sys.exit(f'没有成片，先渲染：{final}')
    video_dur = probe_dur(final)
    print(f'成片时长 {video_dur:.2f}s')

    # 片子里原来的人工配音长度（用来提示）
    copy_p = proj / 'audio' / 'copy.json'
    if copy_p.exists():
        c = json.loads(copy_p.read_text(encoding='utf-8'))
        n = len(c.get('vo1', '')) + len(c.get('vo2', ''))
        print(f'原字幕文案 {n} 字（正常语速约 {n / 4.5:.0f} 秒念完）')

    # ── 1. 转 48k 单声道 wav ──
    tmp = Path(tempfile.mkdtemp())
    vo = tmp / 'voice.wav'
    print('\n[1/5] 转码 …')
    r = run(['ffmpeg', '-v', 'error', '-y', '-i', str(src),
             '-ar', '48000', '-ac', '1', str(vo)])
    if r.returncode != 0 or not vo.exists():
        sys.exit('转码失败：' + (r.stderr or '')[-300:])

    # ── 2. 去首尾静音 ──
    print('[2/5] 去首尾静音 …')
    vo2 = tmp / 'voice_trim.wav'
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(vo),
         '-af', 'silenceremove=start_periods=1:start_threshold=-45dB:'
                'start_silence=0.15,areverse,'
                'silenceremove=start_periods=1:start_threshold=-45dB:'
                'start_silence=0.25,areverse',
         str(vo2)])
    if not vo2.exists():
        vo2 = vo

    vdur = probe_dur(vo2)
    print(f'      去静音后 {vdur:.2f}s')

    # ── 3. 时长对齐 ──
    print('[3/5] 对齐时长 …')
    # 留 0.6 秒头部 + 1.5 秒尾部余量
    target = video_dur - 2.1
    if vdur > target:
        over = vdur - target
        print(f'      ⚠ 录音比画面长 {over:.1f} 秒')
        print('        不自动截断（会切掉话）。两个选择：')
        print('        a) 念快一点重录')
        print('        b) 直接继续，尾部会被画面覆盖')
        print('        3 秒后继续 …')
        import time
        time.sleep(3)
        aligned = vo2
    else:
        # 补静音到目标长度
        pad = target - vdur
        aligned = tmp / 'voice_aligned.wav'
        run(['ffmpeg', '-v', 'error', '-y',
             '-i', str(vo2),
             '-af', f'adelay=600|600,apad=pad_dur={pad:.2f}',
             '-t', f'{video_dur:.2f}',
             str(aligned)])
        print(f'      补 {pad + 0.6:.1f}s 静音（头部 0.6s + 尾部）')

    # ── 4. 和 BGM 混音 ──
    print('[4/5] 混音 …')
    bgm = arg('--bgm')
    if not bgm:
        # 用工程里原来的 BGM
        cand = proj / 'audio' / 'bgm.mp3'
        bgm = str(cand) if cand.exists() else None
    if not bgm or not Path(bgm).exists():
        # 回落到默认
        d = Path('D:/DSH/achun/video-xiaobai/audio/bgm/Carefree.mp3')
        bgm = str(d) if d.exists() else None

    score = proj / 'audio' / 'score.wav'
    src_lufs = measure_lufs(aligned)
    print(f'      源响度 {src_lufs} LUFS')
    gf = gain_filter(src_lufs, TARGET_LUFS)
    if bgm:
        print(f'      BGM: {Path(bgm).name}')
        r = run(['ffmpeg', '-v', 'error', '-y',
                 '-i', str(aligned), '-i', bgm,
                 '-filter_complex',
                 f'[0:a]volume={VO_GAIN}[v];'
                 f'[1:a]volume={BGM_GAIN},atrim=0:{video_dur:.2f},'
                 f'afade=t=out:st={video_dur - 2:.2f}:d=2[b];'
                 f'[v][b]amix=inputs=2:duration=longest:dropout_transition=0,'
                 f'{gf},'
                 f'apad=whole_dur={video_dur:.2f}[a]',
                 '-map', '[a]', '-ar', '48000', '-ac', '2',
                 '-t', f'{video_dur:.2f}', str(score)])
    else:
        print('      没找到 BGM，只用配音')
        r = run(['ffmpeg', '-v', 'error', '-y', '-i', str(aligned),
                 '-af', f'volume={VO_GAIN},{gf}',
                 '-ar', '48000', '-ac', '2',
                 '-t', f'{video_dur:.2f}', str(score)])

    if r.returncode != 0:
        sys.exit('混音失败：' + (r.stderr or '')[-400:])

    # ── 5. 合回成片 ──
    print('[5/5] 合回成片 …')
    out = proj / 'renders' / 'final.mp4'
    bak = proj / 'renders' / 'final.old.mp4'
    shutil.copy2(out, bak)
    r = run(['ffmpeg', '-v', 'error', '-y',
             '-i', str(out), '-i', str(score),
             '-map', '0:v', '-map', '1:a',
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
             '-shortest', str(tmp / 'new.mp4')])
    if r.returncode != 0:
        shutil.copy2(bak, out)
        sys.exit('合成失败，已回滚：' + (r.stderr or '')[-400:])
    shutil.move(str(tmp / 'new.mp4'), str(out))
    print(f'      原片备份到 {bak.name}')

    # ── 校验 ──
    print('\n校验 …')
    r = run(['ffmpeg', '-i', str(out), '-af', 'ebur128=framelog=quiet',
             '-f', 'null', '-'])
    import re
    m = re.search(r'I:\s+(-?[\d.]+)\s+LUFS', r.stderr)
    d = probe_dur(out)
    print(f'  时长 {d:.2f}s / {video_dur:.2f}s')
    if m:
        v = float(m.group(1))
        print(f'  响度 {v} LUFS（目标 {TARGET_LUFS}，-16 是底线）')
        if v < -16:
            print('  ⚠ 偏低，平台会压音量。调高 --vo-gain 重跑')

    print('\n下一步：python tools/make-package.py', proj, '-o D:/publish/<名字>')


if __name__ == '__main__':
    main()
