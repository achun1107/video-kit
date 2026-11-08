# -*- coding: utf-8 -*-
"""生成配音 + SRT + 字幕表。

  python tools/tts.py <工程目录>
  python tools/tts.py <工程目录> --rate +45 --voice zh-CN-YunxiNeural

读 <工程>/audio/copy.json：
  {
    "vo1": "第一段文案……",
    "vo2": "第二段文案……",
    "vo1_at": 0.6,
    "vo2_at": 21.1
  }

产出：
  audio/vo1.mp3  audio/vo1.srt
  audio/vo2.mp3  audio/vo2.srt
  audio/subs.json     ← 合并后的字幕表，film 直接读
  audio/timeline.json ← 段落起止时间，供 film/mix 用
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def opt(a, name, default):
    if name in a:
        return a[a.index(name) + 1]
    return default


def srt_time(s):
    m = re.match(r'(\d+):(\d+):(\d+),(\d+)', s)
    if not m:
        return 0.0
    g = [int(x) for x in m.groups()]
    return g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000


def parse_srt(path):
    txt = open(path, encoding='utf-8').read().strip()
    out = []
    for block in txt.split('\n\n'):
        lines = [l for l in block.split('\n') if l.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r'(.+?)\s*-->\s*(.+)', lines[1])
        if not m:
            continue
        out.append((srt_time(m.group(1)), srt_time(m.group(2)), ''.join(lines[2:])))
    return out


def dur_of(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'default=nw=1:nk=1', str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main():
    a = sys.argv[1:]
    proj = Path(a[0]).resolve() if a else Path('.').resolve()
    audio = proj / 'audio'
    audio.mkdir(parents=True, exist_ok=True)

    copy_path = audio / 'copy.json'
    if not copy_path.exists():
        sys.exit(f'没有 {copy_path}，先写文案')

    copy = json.loads(open(copy_path, encoding='utf-8').read())
    voice = opt(a, '--voice', copy.get('voice', 'zh-CN-YunxiNeural'))
    rate = str(opt(a, '--rate', copy.get('rate', '+45%')))
    pitch = str(opt(a, '--pitch', copy.get('pitch', '+5Hz')))
    # edge-tts 要求 rate 形如 +45%，补上百分号
    if not rate.endswith('%'):
        rate = rate + '%'
    # pitch 要求形如 +5Hz
    if not rate.lower().endswith('hz') and pitch and pitch.replace('+','').replace('-','').isdigit():
        pitch = pitch + 'Hz'
    if pitch and not pitch.lower().endswith('hz'):
        pitch = pitch + 'Hz'
    vo1_at = float(copy.get('vo1_at', 0.6))
    vo2_at = float(copy.get('vo2_at', 21.1))

    subs = []
    timeline = {'vo1_at': vo1_at, 'vo2_at': vo2_at, 'segments': []}

    for key, at in (('vo1', vo1_at), ('vo2', vo2_at)):
        text = copy.get(key)
        if not text:
            continue
        mp3 = audio / f'{key}.mp3'
        srt = audio / f'{key}.srt'
        cmd = ['python', '-m', 'edge_tts', '-t', text, '-v', voice,
               f'--rate={rate}', f'--pitch={pitch}',
               '--write-media', str(mp3), '--write-subtitles', str(srt)]
        print(' '.join(cmd[:6]) + ' …')
        subprocess.run(cmd, check=True)
        d = dur_of(mp3)
        print(f'  {key}: {d:.2f}s → {at:.1f}s 开始，{at + d:.2f}s 结束')

        timeline['segments'].append({'key': key, 'start': at, 'dur': round(d, 3), 'end': round(at + d, 3)})

        if srt.exists():
            for a1, b1, txt in parse_srt(srt):
                subs.append({'a': round(a1 + at, 2), 'b': round(b1 + at, 2), 'zh': txt.strip()})

    subs.sort(key=lambda x: x['a'])
    open(audio / 'subs.json', 'w', encoding='utf-8').write(json.dumps(subs, ensure_ascii=False, indent=2))
    open(audio / 'subs.js', 'w', encoding='utf-8').write('window.SUBS = ' + json.dumps(subs, ensure_ascii=False, indent=2) + ';\n')

    total_end = max((s['end'] for s in timeline['segments']), default=0)
    timeline['content_end'] = round(total_end, 3)
    open(audio / 'timeline.json', 'w', encoding='utf-8').write(json.dumps(timeline, ensure_ascii=False, indent=2))

    print()
    print(f'字幕 {len(subs)} 条 → audio/subs.json / subs.js')
    print(f'配音结束于 {total_end:.2f}s')
    print(f'建议片长 {max(34.8, round(total_end + 1.2, 1))}s')


if __name__ == '__main__':
    main()
