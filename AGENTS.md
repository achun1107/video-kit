# AGENTS.md

给在这个仓库里干活的 AI 助手（Claude Code / Cursor / Copilot Workspace / Codex 等）的说明。

## 这个项目是什么

把 GitHub 仓库或抖音视频，自动变成一条 1080×1920 的竖屏讲解视频。

两种输入：

```bash
node tools/make-video.mjs --repo <github url> --out ./out
node tools/make-video.mjs --douyin "<抖音分享链接>" --out ./out
```

九步流水线：铺骨架 → 仓库就位 → 抽内容 → 截图 → 配音 → 字幕 → 铺模板 → 渲染 → 混音 → 播放页。

## 目录职责

| 目录 | 职责 | 能改吗 |
|---|---|---|
| `engine/vk.js` | 渲染引擎核心（每帧是 t 的纯函数） | **别改**，除非明确要改渲染语义 |
| `engine/vk-kit.js` | 语法件（字幕、数字轮、章节点） | 谨慎改，多片共用 |
| `engine/render.py` | Playwright 截帧 + ffmpeg 合成 | 少动 |
| `tools/film-template.js` | **通用七卡模板**，只读 `window.CONTENT` | 经常改 |
| `tools/make-video.mjs` | 九步编排器 | 经常改 |
| `tools/*.py` | 各步骤的独立脚本（配音、混音、抖音等） | 按需改 |

## 硬约束（改之前先看）

1. **画面必须是 `t` 的纯函数**
   不能有跨帧状态、不能用 `Math.random()`、不能用 `Date.now()`。
   随机一律用 `hash(i)`。否则 `--det` 会报 `NOT deterministic`。

2. **不要用 `ctx.shadow*`**
   `shadowBlur` 在多图合成时破坏确定性。要阴影就用深色填充 + 描边模拟。

3. **多图合成先烤到离屏 canvas**
   单帧里 `drawImage` 超过 3 次且带变换，会影响确定性。做法见 `buildWallCanvas()`。

4. **别把同色系文字压在同色系背景上**
   典型翻车：章节号用了分类色，背景也是分类色 → 数字看不见。

5. **别在文字密集的卡片里再贴文字密集的截图**
   两者会打架。截图要么给足空间，要么不放。

## 改完怎么验

```bash
python engine/render.py <工程目录> --stills 2.0 6.0 10.0   # 抽几帧看
python engine/render.py <工程目录> --det                    # 确定性检查
python engine/render.py <工程目录> --sheet 12               # 12 格总览图
```

`--det` 必须输出 `deterministic`，否则不要提交。

## 内容从哪来

`film.js` 只读 `window.CONTENT`（由 `content.json` 生成），**不写死任何项目信息**。
字段缺了对应那张卡就跳过，不报错。字段清单见 README 的「content.json」一节。

文案在 `audio/copy.json`，`variants` 里保留模板稿和参考稿两档。

## 提交约定

```
<type>: <一句话>

<为什么这么改，不是改了什么>
```

`type` 用 `feat` / `fix` / `docs` / `chore` / `refactor`。

## 不要做的事

- 不要提交 `engine/fonts/`（43MB，跑 `get_fonts.py` 生成）
- 不要提交 `renders/`、`review/`、`_repos/`
- 不要提交 `audio/*.mp3` / `audio/*.srt`（只有 `audio/bgm/` 进库）
- 不要在代码里内联 token / key，走环境变量 `GITHUB_TOKEN`
