# video-kit

[![License: MIT](https://img.shields.io/badge/license-MIT-1f6feb.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%E2%89%A518-3c873a.svg)](package.json)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-3776ab.svg)](https://www.python.org)
[![Runtime deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)](tools/make-video.mjs)
[![Deterministic](https://img.shields.io/badge/render-deterministic-8b5cf6.svg)](docs/ARCHITECTURE.md)

**一条命令，把 GitHub 仓库或者抖音视频变成一条竖屏讲解视频。**

输入一个仓库地址（或一条抖音分享链接），输出 1080×1920 / 34.8 秒 / 带中文解说和配乐的成片。
卡片、截图、字幕、音效、混音全部自动。

![pipeline](assets/pipeline.png)

```bash
# 输入 1：GitHub 仓库
node tools/make-video.mjs --repo https://github.com/webkubor/dsh-bloom-theme --out ./my-video

# 输入 2：抖音分享链接
node tools/make-video.mjs --douyin "https://v.douyin.com/xxxxxx/" --out ./my-video
```

---

## 看看出片长什么样

![demo](assets/demo-frames.png)

一条真实产出的片子（讲 [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)）：

▶ **[看完整成片 demo.mp4（34.8s）](https://github.com/achun1107/video-kit/releases/download/v1.0.0/demo.mp4)**

---

## 快速开始

```bash
git clone https://github.com/achun1107/video-kit
cd video-kit

python engine/get_fonts.py                    # 14 个开源字体，43MB，只下一次
pip install playwright edge-tts numpy scipy pillow
python -m playwright install chrome

node tools/make-video.mjs --repo <仓库地址> --out ./out
```

需要 **Node ≥ 18**、**Python 3.10+**，`ffmpeg` 在 PATH 里。

出片在 `out/renders/final.mp4`，播放页在 `out/renders/player.html`。

---

## 它做了什么

七张卡，固定结构，内容全部来自仓库：

| 卡 | 内容 |
|---|---|
| 1 | 封面：emoji + 名字 + 一句话 + 三个标签 |
| 2 | 数字墙：star / fork / 功能数 |
| 3 | GitHub 截图（带放大圈选） |
| 4 | 特性列表（前 4 条） |
| 5 | 亮点数字 |
| 6 | 清单（章节目录 / 配色表） |
| 7 | 结论 |

抖音视频走同一套流程，只是多了一步「先反查视频里讲的是哪个仓库」。

### 实测样例

| 输入 | 结果 |
|---|---|
| `webkubor/dsh-bloom-theme` | 15 色块墙 + 真实界面截图 + 4.5:1 大数字 |
| `webkubor/xiaobai-kanban` | 14 章目录 + 术语对照 + 费用柱状图 |
| `heygen-com/hyperframes` | 8 万 star 数字墙 + 四步流程 |
| 抖音「Codex 自动化链路」 | 自动识别出 `heygen-com/hyperframes` 并出片 |

---

## 为什么快

**画面是 `t` 的纯函数。** 没有跨帧状态、没有随机数，任意时刻都能直接算出一帧。

所以：

```bash
python engine/render.py <工程> --stills 10.5   # 直接看第 10.5 秒
python engine/render.py <工程> --clip 0 12     # 只渲前 12 秒
python engine/render.py <工程> --det           # 两次渲染必须一模一样
```

`--det` 通过是整个项目的地基——没有它，改一版画面要等 5 分钟才知道对不对。

**内容层与画面层分离。** `film.js` 只读 `content.json`，不写死任何项目信息。
字段缺了那张卡就跳过，不报错。换一个仓库出片，理论上不用改代码。

**文案是唯一必须人写的部分。** 其余全部自动。

---

## 参数

```
--repo <url|目录>      输入 GitHub 仓库
--douyin <分享链接>    输入抖音视频
--out <目录>           默认 ./video-out
--skip-render          只做到「配音 + 模板」，不渲染
--reset-film           用模板覆盖已有的 film.js
--reset-html           重新生成 index.html
--music <mp3>          换配乐，默认 Carefree
--asr-model <size>     抖音转写模型，默认 small
--try <N>              抖音逐条试几条，默认 4
--video <id>           抖音指定某条视频
```

环境变量 `GITHUB_TOKEN` 有值时，会用 API 抽内容（避免 403 和 clone 超时）。

---

## 抖音链路

分享链接 → 抓列表（带点赞数）→ 逐条试 → 下载 → 本地转写 → 反查仓库 → 出片。

**为什么要逐条试**：点赞最高的那条往往不是 GitHub 项目（比如讲 ChatGPT 内置功能的），
盲选第一条必然失败。实测 5 条高赞视频：

| 点赞 | 识别出的仓库 | |
|---|---|---|
| 18,470 | — | 不是 GitHub 项目，正确判为「无仓库」 |
| 15,930 | `bytedance/UI-TARS-desktop` | ✅ |
| 11,979 | `heygen-com/hyperframes` | ✅ |
| 3,724 | `Renhuai123/ziwei-doushu` | ✅ |
| 373 | `microsoft/agent-lightning` | ✅ |

反查靠三样东西：口播里的 **star 数**（最强指纹）、**公司名**（字节→bytedance）、
**jieba 关键词**。三样都命中且领先第二名够多才采信，否则报「没把握」而不是硬凑。

细节见 [架构说明](docs/ARCHITECTURE.md#抖音链路)。

---

## 文档

| 文档 | 内容 |
|---|---|
| [完整用法](docs/USAGE.md) | 参数、字段、时间轴、配色、配乐 |
| [常见问题](docs/FAQ.md) | 装不上、渲不出来、`--det` 不过、文字重叠 |
| [架构说明](docs/ARCHITECTURE.md) | 为什么每帧是纯函数、三层职责、扩展点 |
| [变更记录](CHANGELOG.md) | 版本历史 + 踩过的坑 |
| [参与贡献](CONTRIBUTING.md) | PR 标准、代码规范、提交信息格式 |
| [安全策略](SECURITY.md) | 报告漏洞、它会碰什么、不会碰什么 |
| [AGENTS.md](AGENTS.md) | 给 AI 助手的仓库行为准则 |
| [llms.txt](llms.txt) | 给 LLM 的导读 |

---

## 目录

```
engine/
  vk.js          渲染引擎（每帧是 t 的纯函数）
  vk-kit.js      语法件：字幕、数字轮、章节点、圈选
  render.py      Playwright 逐帧截图 → ffmpeg
  audio.py       合成配乐与音效
  get_fonts.py   下载 14 个开源字体（不进库）

tools/
  make-video.mjs     九步编排器
  film-template.js   通用七卡模板
  tts.py             edge-tts 配音 + SRT + 字幕表
  mix.py             三层混音（人声/音效/配乐）
  extract-content.mjs 仓库 → content.json
  repo-content.py    走 API 生成 content.json（避开 clone 超时）
  shot-github.py     截 GitHub 页
  make-player-html.py 自包含播放页
  douyin-rank.py     抖音列表 + 点赞数
  douyin-download.py 提取 mp4 直链下载
  transcribe-local.py faster-whisper 转写
  repo-finder.py     从转写反查仓库
  asrfix.py          whisper 中文误听纠正
  reverse-batch.py   批量逆向高赞视频
  script-writer.py   生成两档文案

docs/              用法、FAQ、架构
audio/bgm/         6 首免版权配乐
```

---

## 已知限制

1. **文案必须人写** — 自动生成的是通用模板稿，读起来是套话
2. **私有仓库不行** — 抽内容要读文件
3. **渲染 3–6 分钟** — 1044 帧，慢是正常的
4. **抖音需要能访问抖音** — 网络不通就没法下载
5. **没有测试** — 只有 CI 里的语法和结构检查，没有单元测试

---

## 授权

MIT，见 [LICENSE](LICENSE)。

字体是 SIL OFL 1.1，配乐是 CC BY 4.0（Kevin MacLeod），第三方授权详见 [NOTICE](NOTICE)。
