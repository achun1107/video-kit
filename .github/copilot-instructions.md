# Copilot 定制指令

本仓库的 AI 编码规则。与 [AGENTS.md](../AGENTS.md) 同步维护，冲突时以 AGENTS.md 为准。

## 项目概要

video-kit：GitHub 仓库 / 抖音视频 → 1080×1920 竖屏讲解视频。
Node.js（工具与引擎）+ Python（渲染、配音、混音）。

## 技术栈

- `engine/vk.js` — 自研 Canvas 渲染引擎，无第三方依赖
- `engine/render.py` — Playwright + ffmpeg
- `tools/*.py` — edge-tts、faster-whisper、jieba、numpy/scipy
- `tools/*.mjs` — 纯 Node，无构建步骤

## 代码风格

- Python：4 空格缩进，函数名 snake_case，无类型标注（现有代码没标注，保持一致）
- JavaScript：2 空格，`const` 优先，箭头函数
- 注释用中文，写「为什么」不写「做什么」
- 错误信息用中文，前缀 `×`

## 绝对不要

```js
// ❌ 破坏确定性
ctx.shadowColor = '#000';
ctx.shadowBlur = 20;

// ❌ 跨帧状态
let counter = 0;
counter += 1;

// ❌ 非纯函数
const s = Math.random();
```

```js
// ✅ 正确做法
fr.rect(x, y, w, h, { fill: '#000', a: 0.5 });   // 阴影用半透明矩形
const s = hash(i * 1.7 + 3);                      // 随机用种子哈希
```

## 改动后必须验

```bash
python engine/render.py <工程> --det
```

输出必须是 `deterministic`。

## 提交前

- 不要提交 `engine/fonts/`、`renders/`、`review/`、`_repos/`
- 不要内联密钥，用环境变量 `GITHUB_TOKEN`
- commit message 用 `<type>: <描述>`，`type` ∈ {feat, fix, docs, chore, refactor}

## 文件职责边界

| 改这个 | 不要动那个 |
|---|---|
| `tools/film-template.js`（卡片布局） | `engine/vk.js`（渲染语义） |
| `tools/make-video.mjs`（流程编排） | `engine/render.py`（截帧逻辑） |
| `film.js` 的 `C`/`T`/`SUBS`（配色/时间轴） | `engine/vk-kit.js`（共用语法件） |

需要动 `engine/` 的时候，先在 PR 描述里说明为什么非动不可。
