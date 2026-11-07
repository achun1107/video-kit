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
| **主页分享** | `/share/user/<sec_uid>` | 打开主页，拦截 API + 滚动抓视频列表 |

拿到视频后的流程：

```
下载原片（提取 mp4 直链，绕过 yt-dlp）
  ↓
本地转写（faster-whisper，不依赖网络）
  ↓
从转写文本 + 标题里找仓库
  ↓  （转写会把英文专名听错，映射表带误听变体：
  ↓    HyperFrames → "Happy Frames" / video-use → "Videos"）
用 GitHub API 生成 content.json（大仓库 clone 会超时，API 更快）
  ↓
走原来的出片流程
```

**抖音反爬是怎么绕过的**：yt-dlp 会报 `Fresh cookies are needed`，即使从浏览器导出 cookie 也不行。所以改成用 Playwright 打开页面，直接从 `RENDER_DATA` 和 `video[src]` 里挖 mp4 直链，并把 `playwm` 换成 `play` 去水印。

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
