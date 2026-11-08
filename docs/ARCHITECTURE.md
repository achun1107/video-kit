# 架构

## 一句话

每个画面都是时间 `t` 的纯函数。内容层和画面层彻底分开。

```
content.json ──┐
               ├──> film.js ──> vk.js ──> Canvas ──> Playwright ──> ffmpeg ──> mp4
audio/subs.js ─┘                                                              │
                                                                              ▼
audio/vo1.mp3 ────────────────────────────────────────> mix.py ──────> final.mp4
audio/score.wav ──────────────────────────────────────┘
```

## 为什么「每帧是 t 的纯函数」

传统视频渲染是「上一帧 → 下一帧」的增量更新，好处是快，坏处是：

- 不能随机 seek（要重放前面所有帧）
- 不能只渲一段（从头跑）
- 结果不可复现（一旦有状态泄漏）
- 改一行要全片重渲

vk.js 的做法是每帧从零算：`draw(fr, t)` 拿到时间和画布，从头画一遍。

代价是慢（1044 帧要 3–6 分钟），换来的是：

```bash
python engine/render.py <工程> --stills 10.5    # 直接渲第 10.5 秒
python engine/render.py <工程> --clip 0 12      # 只渲前 12 秒
python engine/render.py <工程> --det            # 两次结果必须一致
```

这三条能力是整个工作流的基础——没有它们，改一版画面要等 5 分钟才知道对不对。

### 怎么保证纯

- 随机数一律 `hash(i)`，`i` 是固定的索引
- 不能用 `Math.random()` / `Date.now()` / 跨帧变量
- 多图合成先烤到离屏 canvas（单次 `drawImage` 才稳定）
- 不用 `ctx.shadow*`（`shadowBlur` 在多图层下不稳定）

`--det` 就是把这四条变成可检验的：打乱顺序渲两遍，比 md5。

## 三层职责

### 引擎层 `engine/`

| 文件 | 职责 | 变更频率 |
|---|---|---|
| `vk.js` | Canvas 渲染、时间轴、确定性保证 | 极低（改动影响所有片子） |
| `vk-kit.js` | 语法件：字幕、数字轮、章节点、圈选 | 低（多片共用） |
| `render.py` | Playwright 截帧 + ffmpeg 合成 | 低 |
| `audio.py` | 合成配乐与音效 | 低 |

### 内容层 `content.json` + `audio/copy.json`

从被讲解的仓库抽出来的数据，加上人写的文案。

这一层是**唯一需要人改**的。其他都能自动。

### 画面层 `film.js`

七张卡的具体实现。只读 `window.CONTENT` 和 `window.SUBS`，不写死任何项目信息。

换一个仓库出片，理论上不用改 `film.js`。

## 流水线 `tools/make-video.mjs`

```
step 0  铺骨架      从 KIT 复制 engine/ tools/ 字体 index.html
step 0.5 抖音（可选） 抓列表 → 逐条试 → 下载 → 转写 → 反查仓库
step 1  仓库就位    浅克隆 / 本地目录
step 2  抽内容      extract-content.mjs 或 repo-content.py → content.json
step 3  截图        shot-github.py → assets/repo.png
step 4  配音        tts.py → vo1.mp3 + vo1.srt
step 5  字幕        tts.py → subs.json + subs.js + timeline.json
step 6  铺模板      film-template.js → film.js
step 7  渲染        render.py → raw.mp4
step 8  混音        audio.py + mix.py → final.mp4
step 9  播放页      make-player-html.py → player.html
```

每一步都是独立脚本，可以单独跑、单独调试。

## 抖音链路

```
分享链接
  ↓  302
v.douyin.com → iesdouyin.com/share/{video|user}/<id>
  ↓  douyin-rank.py（Playwright + 拦截 XHR + 滚动）
视频列表（带 digg_count、视频标题）
  ↓  逐条试，最多 --try 条
下载（douyin-download.py：提取 mp4 直链，playwm → play 去水印）
  ↓
转写（transcribe-local.py：faster-whisper，numpy 输入绕开 PyAV 版本问题）
  ↓
纠正误听（asrfix.py：Gatehub→GitHub、紫围斗树→紫微斗数 等）
  ↓
反查仓库（repo-finder.py：star 指纹 + jieba 关键词 + 公司→org + 置信度）
  ↓  没把握就换下一条
content.json → 走正常出片流程
```

### 为什么逐条试

点赞最高的那条往往不是 GitHub 项目（比如讲 ChatGPT 内置功能的），
盲选第一条必然失败。实测 5 条视频，最高赞那条就没有仓库。

### 为什么不用 yt-dlp

抖音要「新鲜的 cookie」（`Fresh cookies are needed`），即使从浏览器导出 cookie 也不行。
所以改成用 Playwright 打开页面，直接从 `RENDER_DATA` 和 `video[src]` 里挖 mp4 直链。

## 混音

三层，实测参数：

| 层 | 增益 | 说明 |
|---|---|---|
| 人声 | `--vo-gain 2.0` | edge-tts，YunxiNeural +45% 语速 |
| 音效 | `--bg 0.06` | 换卡和弦、字幕 tick、转场 thud |
| 配乐 | `--music-gain 0.075` | 真音乐垫底 |

整体走 `loudnorm -13 LUFS`，峰值锁 `-1.4 dBTP`。

人声领先配乐 19.2dB 是实测出来的播客级比例——比这个低人声就被糊住，
比这个高配乐就听不见了。

## 扩展点

| 想加什么 | 改哪 |
|---|---|
| 新输入源（B 站、小红书） | `make-video.mjs` 开头加一块，参考 `--douyin` |
| 新卡片类型 | `film-template.js` 加 `card8`，`segs` 数组里挂上 |
| 新配色 | `film.js` 的 `C` 对象 |
| 新转场 | `vk-kit.js`，但要保证是 `t` 的纯函数 |
| 新音效 | `engine/audio.py` 的合成函数 |
