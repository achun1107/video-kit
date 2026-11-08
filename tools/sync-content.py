# -*- coding: utf-8 -*-
"""content.json → content.js 同步。

## 为什么要单独做

渲染时 film.js 读的是 `window.CONTENT`，那个值由 content.js 注入。
但 content.json 改了（比如补了 star）之后，content.js 不会自动更新 ——
它是 make-video.mjs 在铺骨架那一步生成的旧快照。

结果就是：封面和文案都有 133 star，视频里却没有。
这个 bug 不渲一遍看不出来。

  python tools/sync-content.py <工程目录>
  python tools/sync-content.py D:\\four\\ganhuoju
"""
import json
import sys
from pathlib import Path


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    cj = proj / 'content.json'
    if not cj.exists():
        sys.exit(f'没有 {cj}')

    data = json.loads(cj.read_text(encoding='utf-8'))
    body = json.dumps(data, ensure_ascii=False, indent=2)
    js = f'window.CONTENT = {body};\n'

    out = proj / 'content.js'
    out.write_text(js, encoding='utf-8')

    stats = data.get('stats') or {}
    print(f'{out}')
    print(f'  star={stats.get("star")}  '
          f'features={len(data.get("features") or [])}')


if __name__ == '__main__':
    main()
