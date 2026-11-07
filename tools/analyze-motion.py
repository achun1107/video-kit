# -*- coding: utf-8 -*-
"""量化分析一段画面：标题区域的白字占比（= 字体大小变化）、整体变化率（= 转场强度）。

  python tools/analyze-motion.py <视频> --start 0 --end 2 --step 0.05
  python tools/analyze-motion.py <视频> --region title    # title / full / bottom
"""
import subprocess, sys, io
from pathlib import Path
from PIL import Image
import numpy as np

src = sys.argv[1]
def opt(n, d): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d

start = float(opt("--start", 0))
end = float(opt("--end", 2))
step = float(opt("--step", 0.05))
region = opt("--region", "title")
W, H = 1080, 1920

REGIONS = {
    "title":  (0, 0, W, int(H * 0.22)),        # 顶部标题区
    "bottom": (0, int(H * 0.80), W, H),        # 底部字幕区
    "full":   (0, 0, W, H),
}
x0, y0, x1, y1 = REGIONS.get(region, REGIONS["title"])

# 用 ffmpeg 抽帧到内存
cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-to", str(end), "-i", src,
       "-vf", f"fps=1/{step}", "-f", "image2pipe", "-vcodec", "png", "-"]
out = subprocess.run(cmd, capture_output=True).stdout

# PNG 流按签名切分
sig = b"\x89PNG\r\n\x1a\n"
parts, idx = [], out.find(sig)
while idx >= 0:
    nxt = out.find(sig, idx + 1)
    parts.append(out[idx:nxt if nxt > 0 else len(out)])
    idx = nxt

prev = None
print(f"{'时刻':>7} {'亮像素占比':>10} {'相对首帧':>9} {'帧间变化':>9}")
base = None
for i, p in enumerate(parts):
    t = start + i * step
    im = Image.open(io.BytesIO(p)).convert("L").crop((x0, y0, x1, y1))
    a = np.asarray(im, dtype=np.float32) / 255.0
    bright = float((a > 0.75).mean())          # 白字占比
    if base is None:
        base = bright
    diff = 0.0 if prev is None else float(np.abs(a - prev).mean())
    print(f"{t:7.2f} {bright*100:9.3f}% {(bright/base if base else 0):8.2f}x {diff*100:8.2f}%")
    prev = a
