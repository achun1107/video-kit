# 常见问题

## 装不上 / 跑不起来

### `python engine/get_fonts.py` 下载失败

字体从 `raw.githubusercontent.com` 拉，国内经常连不上。三个办法：

1. 挂代理再跑
2. 手动下：脚本会打印失败的文件对应的 URL，浏览器打开另存到 `engine/fonts/`
3. 换字体：`index.html` 里的 `@font-face` 改成系统已有的中文字体

缺字体的表现是渲染卡住不动，最后报 `Page.wait_for_function: Timeout 180000ms exceeded`。
因为 `document.fonts.ready` 永远等不到。

### `playwright install chrome` 很慢

用系统已有的 Chrome 也行，把 `engine/render.py` 里 `channel='chrome'` 改成 `channel='msedge'`
（Windows）或者删掉 `channel` 参数用 Playwright 自带的 Chromium。

### `ffmpeg` 找不到

Windows 装法：

```powershell
winget install ffmpeg
# 或者 scoop install ffmpeg
```

装完新开一个终端，`ffmpeg -version` 能出东西就行。

### `edge-tts` 报 `Invalid rate '+45'`

版本问题。`rate` 必须写成 `+45%`（带百分号）。已经在 `tools/tts.py` 里自动补了，
如果还报错，检查 `audio/copy.json` 里的 `rate` 字段。

---

## 渲染问题

### `--det` 报 `NOT deterministic`

画面有非确定性来源。常见三种：

1. **用了 `ctx.shadow*`** — `shadowBlur` 在多图合成时结果不稳定。改成深色填充 + 描边。
2. **单帧 `drawImage` 超过 3 次带变换** — 先烤到一个离屏 canvas，再单次贴上去。
   参考 `buildWallCanvas()` 的写法。
3. **用了 `Math.random()` / `Date.now()`** — 一律换成 `hash(i)`。

报错信息里会带坐标 `[t, x, y, w, h]`，按坐标找是哪张卡。

### 卡片里是灰色占位条，没内容

`index.html` 缺 `content.js` 或 `window.VK_SIZE`。

```bash
grep -c 'content.js' index.html        # 应该是 1
grep -c 'VK_SIZE' index.html           # 应该是 1
```

缺的话用 `--reset-html` 重新生成，或者直接从 `tools/index.template.html` 复制。

### 画幅变成横屏了

同上，缺 `window.VK_SIZE = { w: 1080, h: 1920 }`。默认会退回 1920×1080。

### 文字重叠 / 看不见

两个经典翻车：

1. **同色系文字压同色系背景** — 章节号用了分类色，背景也是分类色。
   改用 `C.ink` 这种对比色。
2. **文字密集的卡片里又贴了文字密集的截图** — 两者打架。
   截图要么给足空间单独一卡，要么不放。

### 渲染很慢

正常。1044 帧、每帧 Playwright 截图，3–6 分钟。

想快一点：

```bash
python engine/render.py <工程> --clip 0 12    # 只渲前 12 秒
python engine/render.py <工程> --jobs 3       # 并发（偶尔会超时）
```

---

## 内容问题

### 抽出来的内容不对

`extract-content.mjs` 从 README 猜。README 结构不规律就抽不准。

直接改 `content.json` 更快。字段说明见 README。

### 大仓库 clone 超时

180 秒上限。两个办法：

1. 用 `tools/repo-content.py` 走 GitHub API，不 clone
2. 手动把仓库放到 `_repos/<name>/`

### 文案出来是通用套话

对，模板稿就是这样。文案是**唯一必须人写**的部分。

```bash
# 改完重跑
vim audio/copy.json
python tools/tts.py <工程>
```

---

## 抖音相关

### 下载失败，报 `Fresh cookies are needed`

`douyin-download.py` 已经绕过了这个问题（提取 mp4 直链，不走 yt-dlp）。
如果还失败，通常是抖音页面结构变了，需要更新 `find_play_urls()` 里的正则。

### 抓不到视频列表

主页可能是动态加载的。脚本会滚动 10 次，如果还是 0 条：

- 抖音要登录才能看（部分账号）
- 或者页面改版了

### 转写很慢

`small` 模型在 CPU 上大约 1/3 实时速度。30 秒视频约 10 秒转完。

想快用 `--asr-model tiny`（准确率下降），想准用 `medium`（慢 3 倍）。

### 识别出的仓库不对

口播里没念仓库名，只能猜。三个改进方向：

1. 看 `found.json` 里的 `candidates`，手工确认
2. 用 `--repo <owner/repo>` 直接指定
3. 补 `asrfix.py` 的误听表（whisper 经常把英文专名听错）

---

## 其他

### 配乐可以换吗

`audio/bgm/` 里 6 首 Kevin MacLeod 的 CC BY 曲目，也可以 `--music <你的mp3>`。

注意音量比例：人声领先配乐 19.2dB 是实测的播客级比例，自己换曲后可能要在
`tools/mix.py` 里调 `--music-gain`。

### 能不能商用

代码 MIT，随便用。但：

- 字体是 SIL OFL，可以商用
- 配乐是 CC BY，**必须署名** Kevin MacLeod
- 生成的视频里展示的第三方项目，版权归各自项目

### 为什么只有竖屏

目标场景是抖音/视频号。想改横屏，把 `index.html` 的 `VK_SIZE` 和 canvas CSS 改掉，
再把 `film.js` 里的 `W`/`H` 相关布局重排。
