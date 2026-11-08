# video-kit

**一条命令，把 GitHub 仓库——或者一条抖音视频——变成一条竖屏讲解视频。**

输出 1080×1920 / 34.8 秒 / 带中文解说和配乐的成片，卡片、截图、字幕、音效全部自动。

```bash
# 输入 1：GitHub 仓库
node tools/make-video.mjs --repo https://github.com/webkubor/dsh-bloom-theme --out ./my-video

# 输入 2：抖音分享链接（自动下载原片 → 转写 → 找出视频里讲的仓库 → 重新出片）
node tools/make-video.mjs --douyin "https://v.douyin.com/xxxxxx/" --out ./my-video
```

> **已验证**：
> - 从干净 clone 出发，`get_fonts.py` 下 14 个字体（43.4MB），`--skip-render` 全流程走通
> - 抖音链路实测：主页分享链接 → 抓到 20 条视频 → 下载原片 → 本地转写 306 字 →
>   识别出 `heygen-com/hyperframes`（80464 star）→ 生成 content.json + 9 条字幕

---

## 两种输入

### 1. GitHub 仓库

```bash
node tools/make-video.mjs --repo <url 或本地目录> --out <工程目录>
```

浅克隆（180 秒上限，大仓库会超时）→ 抽内容 → 截图 → 配音 → 渲染。

### 2. 抖音视频链接

```bash
node tools/make-video.mjs --douyin "https://v.douyin.com/xxxx/" --out <工程目录>
```

抖音分享链接有两种，脚本都能处理：

| 类型 | 重定向到 | 处理 |
|---|---|---|
| **视频分享** | `/share/video/<id>` | 直接拿到 id |
| **主页分享** | `/share/user/<sec_uid>` | 打开主页，拦截 API + 滚动抓视频列表（带点赞数） |

拿到视频后的流程：

```
抓列表（含点赞数，按赞降序）
  ↓
逐条试：下载 → 本地转写 → 反查仓库
  ↓  （第一条没识别出仓库就自动换下一条，最多 --try 条）
命中仓库 → GitHub API 生成 content.json → 走原来的出片流程
```

**为什么是「逐条试」**：点赞最高的那条往往不是 GitHub 项目
（比如讲 ChatGPT 内置功能的），盲选第一条必然失败。

---

## 批量逆向高赞视频

```bash
# 1. 抓主页视频列表，按点赞排序
python tools/douyin-rank.py "https://v.douyin.com/xxxx/" -o rank.json --max 40

# 2. 逆向前 N 条：下载 + 转写 + 找仓库
python tools/reverse-batch.py rank.json -o reversed.json --top 5

# 3. 单独确认某条的仓库（带候选和置信度）
python tools/repo-finder.py douyin/asr/<id>.json --title "视频标题" -o found.json
```

实测 5 条高赞视频的结果（账号「AI科技视野」）：

| 点赞 | 视频 | 识别出的仓库 | |
|---|---|---|---|
| 18,470 | GPT 调色 | — | 不是 GitHub 项目，正确判为「不采信」 |
| 15,930 | 字节开源黑科技 | `bytedance/UI-TARS-desktop` | ✅ |
| 11,979 | Codex 自动化链路 | `heygen-com/hyperframes` | ✅ |
| 3,724 | 紫微斗数排盘 | `Renhuai123/ziwei-doushu` | ✅ |
| 373 | 微软 Agent 训练 | `microsoft/agent-lightning` | ✅ |

**4/5 命中，剩下 1 条正确识别为「没有仓库」。**

### 怎么做到的

口播里找仓库有三个坑，逐个填：

1. **转写误听**——whisper 把专名听错：`Gatehub`→GitHub、`紫围斗树`→紫微斗数、
   `温软`→微软、`CodeS`→Codex、`Happy Frames`→HyperFrames。
   用 `tools/asrfix.py` 的纠正表（一次性替换，循环 replace 会叠出 `HyperFramess`）。

2. **关键词**——滑窗切中文会切出「紫微斗数的开」这种碎片，搜什么都搜不到。
   改用 `jieba.analyse.extract_tags`（TF-IDF）。

3. **排序**——口播经常报 star 数（「3.6万star」「一点八万star」），这是最强指纹。
   `tools/repo-finder.py` 把 star 接近度 + 公司（字节→bytedance、微软→microsoft）
   + 关键词命中算成总分，并要求「绝对分 ≥60 且领先第二名 ≥4」才采信，
   否则报告「没把握」而不是硬凑一个。

---

## 两档文案

```bash
python tools/script-writer.py <工程目录>                          # 只用模板稿
python tools/script-writer.py <工程目录> --from-asr douyin/asr/x.json  # 生成模板稿 + 参考稿
```

| 档 | 依据 | 特点 |
|---|---|---|
| **模板稿** | 只读 `content.json`，套固定骨架 | 永远能出片，信息密度低 |
| **参考稿** | 借原视频的转写结构和节奏，换主语 | 有原片时质量明显更高 |

两档都写进 `audio/copy.json` 的 `variants` 字段，`vo1`/`vo2` 是最终采用的那档（`--style` 指定）。

---

## 它长什么样

七张卡，固定结构，内容全部来自仓库：



```
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ 1 封面  │→ │ 2 数字墙 │→ │ 3 截图  │→ │ 4 特性  │
│ emoji   │  │ 大数字   │  │ 放大圈选 │  │ 前四条  │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
┌─────────┐  ┌─────────┐  ┌─────────┐
│ 5 亮点  │→ │ 6 清单  │→ │ 7 结论  │
└─────────┘  └─────────┘  └─────────┘
```

实测样例：

| 仓库 | 片子 | 特点 |
|---|---|---|
| `webkubor/xiaobai-kanban` | 34.8s | 14 章目录 + 术语对照 + 费用柱状图 |
| `webkubor/dsh-bloom-theme` | 34.8s | 15 色块墙 + 真实界面截图 + 4.5:1 大数字 |

---

## 为什么快

画面是 **t 的纯函数**——没有跨帧状态、没有随机数，任意时刻都能直接算出一帧。

所以：
- 可以 `--clip 0 12` 只渲染一段验证
- `--det` 能验证两次渲染完全一致
- 改一行代码重渲，结果可复现

渲染引擎来自 [vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film) 的 vk.js（Canvas 逐帧 + Playwright 截图 + ffmpeg 合成），这套工作流在它之上加了内容抽取、配音、混音和编排。

---

## 安装

需要 **Node ≥ 18** 和 **Python 3.10+**。

```bash
# 1. 字体（43MB，只下载一次）
python engine/get_fonts.py

# 2. Python 依赖
pip install playwright edge-tts numpy scipy pillow
python -m playwright install chrome

# 3. ffmpeg 要在 PATH 里
ffmpeg -version
```

---

## 用法

### 一条命令出片

```bash
node tools/make-video.mjs --repo <仓库> --out <目录>
```

九步：铺骨架 → 克隆 → 抽内容 → 截图 → 配音 → 字幕 → 铺模板 → 渲染 → 混音 → 播放页。

### 先看再跑（不渲染，几秒钟）

```bash
node tools/make-video.mjs --repo <仓库> --out ./试跑 --skip-render
```

### 改文案再出片（推荐）

第一次跑会生成 `audio/copy.json`：

```json
{
  "voice": "zh-CN-YunxiNeural",
  "rate": "+45%",
  "pitch": "+5Hz",
  "vo1_at": 0.6,
  "vo2_at": 21.1,
  "vo1": "第一段（约 20 秒，110-130 字）",
  "vo2": "第二段（约 10 秒，60-80 字）"
}
```

改完重跑，配音、SRT、字幕表全部重新生成，时间轴自动对齐。

> **文案是唯一必须人写的部分。** 其余的自动化都能做，唯独旁白需要理解项目。
> 默认模板稿能出片，但读起来是通用套话。

### 只跑某一步

```bash
python tools/tts.py <工程>                    # 重新配音
python engine/render.py <工程>                # 重新渲染
python tools/mix.py <工程> --vo1 0.6 --vo2 21.1 \
  --bg 0.06 --music-gain 0.075 --music audio/bgm/Carefree.mp3 \
  --vo-gain 2.0 --lufs -13                    # 重新混音
python tools/make-player-html.py <工程>/renders/final.mp4 \
  -o <工程>/renders/player.html               # 生成自包含播放页
```

### 参数

```
--repo <url|目录>     必填
--out <目录>          默认 ./video-out
--skip-render         只做到「配音 + 模板」
--reset-film          用模板覆盖已有的 film.js
--music <mp3>         换配乐，默认 Carefree
```

---

## 内容是怎么抽的

`tools/extract-content.mjs` 从仓库读：

| 来源 | 抽出 |
|---|---|
| `package.json` | `name` `version` `description` `keywords` |
| `README.md` | 首段作 `tagline`，标题列表作 `features` |
| `catalog.md` / `docs/` | 章节表（编号 + 标题）→ `chapters` |
| `index.md` frontmatter | `hero` `features` |

写进 `content.json`，`film.js` 只读它，不写死任何项目信息。

字段缺了那张卡就跳过，不报错。完整字段见下方「content.json」。

---

## 音频怎么配的

三层混音，实测的人声/配乐比是 **19.2 dB**（播客级）：

| 层 | 增益 | 说明 |
|---|---|---|
| 人声 | `--vo-gain 2.0` | edge-tts 生成，YunxiNeural +45% 语速 |
| 音效 | `--bg 0.06` | 换卡和弦、字幕 tick、转场 thud |
| 配乐 | `--music-gain 0.075` | 真音乐垫底 |

整体走 `loudnorm -13 LUFS`，峰值 `-1.4 dBTP`。

配乐用 `audio/bgm/` 里 6 首 Kevin MacLeod（CC BY）：

| 曲目 | BPM | 适合 |
|---|---|---|
| **Carefree** | 100 | 轻快知识类（默认） |
| Life of Riley | 50 | 稳一点 |
| Fluffing a Duck | 60 | 俏皮 |
| Monkeys Spinning Monkeys | 71 | 梗曲 |
| Sneaky Snitch | 22 | 悬疑 |
| Wallpaper | 40 | 最安静 |

---

## 参数

```
--repo <url|目录>      输入 GitHub 仓库（和 --douyin 二选一）
--douyin <分享链接>    输入抖音视频链接（和 --repo 二选一）
--out <目录>          默认 ./video-out
--skip-render         只做到「配音 + 模板」，不渲染
--reset-film          用模板覆盖已有的 film.js
--reset-html          重新生成 index.html
--music <mp3>         换配乐，默认 Carefree
--asr-model <size>    抖音转写用的模型，默认 small（可选 medium / large-v3）
--skip-download       抖音流程跳过下载（复用已有文件）
--reset-asr           抖音流程强制重新转写
```

环境变量 `GITHUB_TOKEN` 有值时，抖音流程会用它调 API 抽内容（避免 403 和 clone 超时）。

---

## content.json

```json
{
  "repo": "owner/name",
  "namePlain": "显示名",
  "emoji": "🌸",
  "headline": "一句话卖点",
  "tagline": "更长一点的描述",
  "version": "0.26.0",
  "accent": "#A873C4",
  "accent2": "#5FA8B2",
  "stats": { "palettes": 15, "deps": 0, "star": 129, "fork": 7 },
  "statLabels": { "palettes": "套配色", "deps": "个依赖" },
  "features": [{ "title": "磨砂玻璃", "desc": "半透 + 模糊" }],
  "chapters": [{ "no": "01", "title": "Agent 是什么" }],
  "palettes": ["黛蓝", "朱砂"],
  "conclusion": ["完全免费", "完全开源", "一键切换"]
}
```

---

## 目录

```
engine/
  vk.js          渲染引擎（每帧是 t 的纯函数）
  vk-kit.js      语法件：字幕、数字轮、章节点、圈选
  render.py      Playwright 逐帧截图 → ffmpeg
  audio.py       合成配乐与音效
  get_fonts.py   下载 14 个开源字体
  fonts/         不随仓库走，跑 get_fonts.py 生成

tools/
  make-video.mjs     ★ 九步编排器
  film-template.js   ★ 通用七卡模板
  tts.py             edge-tts 配音 + SRT + 字幕表
  mix.py             三层混音
  extract-content.mjs 仓库 → content.json
  shot-github.py     截图（含聚焦坐标，给放大圈选用）
  make-player-html.py 自包含播放页
  glyph-metrics.py   量文字几何（调排版）
  analyze-motion.py  量帧差与亮像素（调节奏）

audio/bgm/       6 首免版权配乐
```

---

## 调画面

`film.js` 里七张卡是独立函数，改哪张动哪张：

```js
function card2(fr, lt) {           // 第二张卡
  const k = ss(lt, 0, 0.7);        // 入场进度 0→1
  cardBox(fr, k);                  // 卡片外框
  fr.text('标题', W/2, 490, { font:'sans', size:46, color:C.ink, a: rowA(lt,0) });
  ...
}
```

- `lt` — 这张卡从开始到现在过了几秒
- `rowA(lt, i)` — 第 i 行什么时候出现
- `ss(lt, a, b)` — a→b 秒之间平滑 0→1

---

## 已知限制

1. **文案必须人写** — 自动化只能给通用模板稿
2. **私有仓库不行** — 抽内容要读文件
3. **GitHub 截图可能失败** — 网络或反爬，失败也能出片，只少那张
4. **克隆有 180 秒上限** — 大仓库可能超时，需手工放 `_repos/`
5. **渲染 3–6 分钟** — 1044 帧，慢是正常的

---

## 上传到 GitHub

仓库根目录有一个现成的 `push-to-github.py`，token 只走命令行、不写进 `.git/config`：

```bash
# 1. 建 token：https://github.com/settings/tokens/new  （只勾 repo）
# 2. 推送
python tools/push-to-github.py --token ghp_xxxxxxxx
```

它会验证 token、建仓库、推送，然后把 `origin` 设成不带 token 的干净地址。

不想用命令行的话：`git archive --format=zip -o video-kit.zip HEAD` 打个包，
在 GitHub 网页上新建空仓库，拖进去上传即可。


---

## License

MIT。字体是 SIL OFL 1.1，配乐是 CC BY 4.0（Kevin MacLeod），详见 [LICENSE](LICENSE)。

渲染引擎来自 [vibe-knowledge-film](https://github.com/HeyChengC/vibe-knowledge-film)（MIT）。
