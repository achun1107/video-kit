# -*- coding: utf-8 -*-
"""把人声、音效、背景音乐混进画面。

  python tools/mix.py <工程目录>                              # 人声 + 音效
  python tools/mix.py <工程目录> --music audio/bgm/Carefree.mp3
  python tools/mix.py <工程目录> --vo1 0.6 --vo2 21.1 --bg 0.25 --music-gain 0.075

音量分三层（默认值就是照着"人声远远大于配乐"调的）：
  人声    vo_gain      1.00   ← 主体
  音效    bg           0.22   ← tick / chord 这些点缀，比原来 0.50 收了一半
  配乐    music_gain   0.075  ← 纯音乐垫底，比人声低约 15 dB

配音文件约定：<工程>/audio/vo1.mp3、vo2.mp3（edge-tts 生成）。
音效：<工程>/audio/score.wav（engine/audio.py 生成）。
配乐：任意 mp3/wav，循环铺满全片，首尾各做 0.4s / 1.5s 淡入淡出。
"""
import subprocess, sys
from pathlib import Path


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    proj = Path(a[0]).resolve()

    def opt(name, default):
        if name in a:
            return float(a[a.index(name) + 1])
        return default

    def sopt(name, default):
        if name in a:
            return a[a.index(name) + 1]
        return default

    vo1_at = opt("--vo1", 0.6)
    vo2_at = opt("--vo2", 21.1)
    bg = opt("--bg", 0.06)              # 音效层（实测：只做点缀，别盖人声）
    music_gain = opt("--music-gain", 0.075)   # 背景音乐层（实测人声比它高 14.4 dB）
    vo_gain = opt("--vo-gain", 1.0)
    use_vo = "--no-vo" not in a
    music_path = sopt("--music", None)

    raw = proj / "renders/raw.mp4"
    if not raw.exists():
        sys.exit(f"没有 {raw}，先跑 render.py")
    score = proj / "audio/score.wav"
    vo1 = proj / "audio/vo1.mp3"
    vo2 = proj / "audio/vo2.mp3"
    out = proj / "renders/final.mp4"
    end = dur(raw)

    inputs = ["-i", str(raw)]
    filters = []
    mix_in = []
    idx = 1

    # ── 背景音乐（循环铺满全片，压低垫底）
    if music_path:
        mp = Path(music_path)
        if not mp.is_absolute():
            mp = (proj / music_path).resolve()
        if not mp.exists():
            sys.exit(f"找不到配乐 {mp}")
        inputs += ["-stream_loop", "-1", "-i", str(mp)]
        filters.append(
            f"[{idx}:a]aresample=48000,"
            f"atrim=0:{end:.3f},asetpts=N/SR/TB,"
            f"volume={music_gain},"
            f"afade=t=in:st=0:d=0.6,afade=t=out:st={end - 1.8:.3f}:d=1.8,"
            f"pan=stereo|c0=c0|c1=c0[mu]"
        )
        mix_in.append("[mu]")
        idx += 1

    # ── 音效层（tick / chord / thud）
    if score.exists():
        inputs += ["-i", str(score)]
        filters.append(f"[{idx}:a]aresample=48000,volume={bg}[bg]")
        mix_in.append("[bg]")
        idx += 1

    # ── 人声（主体，最后进 amix，权重最直观）
    if use_vo:
        for path, at, tag in ((vo1, vo1_at, "v1"), (vo2, vo2_at, "v2")):
            if not path.exists():
                print(f"跳过 {path.name}（不存在）")
                continue
            inputs += ["-i", str(path)]
            ms = int(round(at * 1000))
            filters.append(
                f"[{idx}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,"
                f"volume={vo_gain},adelay={ms}|{ms}[{tag}]"
            )
            mix_in.append(f"[{tag}]")
            idx += 1

    if not mix_in:
        sys.exit("没有任何音频输入")

    if len(mix_in) == 1:
        filters.append(f"{mix_in[0]}anull[a]")
    else:
        filters.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:dropout_transition=0[a]")

    # 响度标准化（-16 LUFS / -1.5 dBTP，对齐参考片）
    lufs = opt("--lufs", -16.0)
    if "--no-loudnorm" not in a:
        filters.append(f"[a]loudnorm=I={lufs}:TP=-1.5:LRA=11[an]")
        out_label = "[an]"
    else:
        out_label = "[a]"

    cmd = ["ffmpeg", "-hide_banner", "-y"] + inputs + [
        "-filter_complex", ";".join(filters),
        "-map", "0:v", "-map", out_label,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(out),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"done {out}  video={end:.2f}s audio={dur(out):.2f}s")


if __name__ == "__main__":
    main()
