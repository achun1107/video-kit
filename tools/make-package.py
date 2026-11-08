# -*- coding: utf-8 -*-
"""打发布包：一个目录拿走就能发。

  python tools/make-package.py <工程目录> -o <输出目录>

产出：
  <输出目录>/
    01_成片.mp4
    02_封面-抖音.png
    02_封面-小红书.png
    02_封面-视频号.png
    02_封面-B站.png
    03_发布文案.md
    怎么发.txt

为什么要打包：现在视频、封面、文案分散在工程目录里
（renders/final.mp4、renders/cover-*.png、renders/publish.md），
发布时要在几个路径之间来回找，容易漏。
"""
import json
import shutil
import sys
from pathlib import Path

PLAT_LABEL = {
    'douyin': '抖音',
    'xhs': '小红书',
    'channels': '视频号',
    'bilibili': 'B站',
}

HOWTO = """怎么发
========

一次准备，四个平台都能用。

## 1. 抖音
- 视频：01_成片.mp4
- 封面：02_封面-抖音.png（或上传时从视频选帧）
- 标题：见 03_发布文案.md「抖音」那段
- 话题：同上，复制那行 # 开头的
- 注意：竖屏 1080×1920，时长 34.8 秒，字幕已避开底部 UI 区

## 2. 小红书
- 视频：01_成片.mp4
- 封面：02_封面-小红书.png（3:4，feed 里露出最多）
- 标题：见文案「小红书」段
- 正文：见文案「小红书」段的简介，分段贴
- 注意：小红书竖屏 feed 是 3:4，用错封面会被裁

## 3. 视频号
- 视频：01_成片.mp4
- 封面：02_封面-视频号.png（6:7）
- 标题：见文案「视频号」段（不加 emoji）
- 注意：视频号对纯 AI 配音较敏感，建议加真人出镜或改成自己念

## 4. B站
- 视频：01_成片.mp4
- 封面：02_封面-B站.png（16:9 会自动加黑边，竖屏也能用）
- 标题：见文案「B站」段
- 标签：见文案，B站标签是单独填的，不用 # 号
- 注意：B站可以放更长的版本，这条是 34.8 秒，属于短视频

## 通用检查
- [ ] 封面在手机上缩略图能看清标题（把手机拿远 30cm 看）
- [ ] 字幕没有被平台 UI 挡住（抖音底部 480px 是遮挡区）
- [ ] 前 3 秒有钩子（这条片子的钩子是"133 星的冷门开源项目"）
- [ ] 话题数量对（抖音 3-5 个，小红书 5-8 个，视频号 2-3 个）
"""


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    cp = proj / 'content.json'
    if not cp.exists():
        sys.exit(f'没有 {cp}')
    c = json.loads(cp.read_text(encoding='utf-8'))
    name = c.get('namePlain') or c.get('name') or 'video'

    rdir = proj / 'renders'
    out = Path(arg('-o', str(Path('D:/publish') / name))).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # 1. 成片
    src = rdir / 'final.mp4'
    if not src.exists():
        src = rdir / 'raw.mp4'
    if not src.exists():
        sys.exit('没有成片，先渲染 + 混音')
    shutil.copy2(src, out / '01_成片.mp4')
    size_mb = (out / '01_成片.mp4').stat().st_size / 1048576

    # 2. 封面
    covers = 0
    for plat in PLAT_LABEL:
        p = rdir / f'cover-{plat}.png'
        if p.exists():
            shutil.copy2(p, out / f'02_封面-{PLAT_LABEL[plat]}.png')
            covers += 1

    # 3. 文案
    pm = rdir / 'publish.md'
    if pm.exists():
        shutil.copy2(pm, out / '03_发布文案.md')
    else:
        sys.exit('没有 publish.md，先跑 publish-info.py')

    # 4. 怎么发
    (out / '怎么发.txt').write_text(HOWTO, encoding='utf-8')

    print(f'\n发布包：{out}')
    print(f'  01_成片.mp4        {size_mb:.1f} MB')
    print(f'  02_封面-*.png      {covers} 张')
    print('  03_发布文案.md')
    print('  怎么发.txt')
    print()
    for f in sorted(out.iterdir()):
        print(f'    {f.name}')


if __name__ == '__main__':
    main()
