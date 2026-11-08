# -*- coding: utf-8 -*-
"""把 mp4 压成 base64 内嵌的单文件 HTML —— 这样 DSH 的 HTML 预览器能直接播。

  python tools/make-player-html.py renders/final.mp4 -o renders/player.html
"""
import base64
import os
import subprocess
import sys
import tempfile

src = sys.argv[1]
def opt(n, d): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
out = opt('-o', 'renders/player.html')
crf = opt('--crf', '30')

# 压一个适合内嵌的版本
tmp = os.path.join(tempfile.gettempdir(), 'dshvp_embed.mp4')
if os.path.exists(tmp):
    os.remove(tmp)
subprocess.run([
    'ffmpeg', '-v', 'error', '-y', '-i', src,
    '-vf', 'scale=720:-2',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', crf,
    '-profile:v', 'main', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '96k',
    '-movflags', '+faststart', tmp,
], check=True)

size = os.path.getsize(tmp)
b64 = base64.b64encode(open(tmp, 'rb').read()).decode('ascii')

html = f"""<!doctype html>
<meta charset="utf-8">
<title>小白看板 · 第 01 期</title>
<style>
  html,body{{margin:0;height:100%;background:#0d0d10;overflow:hidden}}
  .wrap{{display:flex;align-items:center;justify-content:center;height:100%;padding:12px;box-sizing:border-box}}
  video{{max-width:100%;max-height:100%;width:auto;height:auto;border-radius:14px;
        box-shadow:0 8px 40px rgba(232,97,60,.25),0 2px 10px rgba(0,0,0,.6);background:#000}}
  .tip{{position:fixed;left:0;right:0;bottom:8px;text-align:center;color:#6b6b73;
       font:11px/1.6 ui-monospace,Consolas,monospace;pointer-events:none}}
</style>
<div class="wrap">
  <video controls autoplay playsinline preload="auto"
         src="data:video/mp4;base64,{b64}"></video>
</div>
<div class="tip">小白也能指挥 Agent · 第 01 期 · {size/1024/1024:.2f}MB 内嵌</div>
"""

os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'{out}  {os.path.getsize(out)/1024/1024:.2f} MB  (视频 {size/1024/1024:.2f} MB → base64 {len(b64)/1024/1024:.2f} MB)')
