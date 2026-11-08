# 完整用法

## 一条命令

```bash
node tools/make-video.mjs --repo <仓库> --out <目录>
node tools/make-video.mjs --douyin "<分享链接>" --out <目录>
```

九步，每步都能单独重跑：

| 步 | 做什么 | 产物 |
|---|---|---|
| 0 | 铺引擎骨架（含字体、index.html） | `engine/` `tools/` `index.html` |
| 1 | 仓库就位（浅克隆 / 本地目录 / API） | `_repos/<name>/` |
| 2 | 抽内容 | `content.json` `content.js` |
| 3 | 截 GitHub 页 | `assets/repo.png` |
| 4 | 生成配音 | `audio/vo1.mp3` `vo1.srt` |
| 5 | 字幕表 | `audio/subs.json` `subs.js` `timeline.json` |
| 6 | 铺影片模板 | `film.js` |
| 7 | 渲染画面 | `renders/raw.mp4` |
| 8 | 配乐 + 混音 | `renders/final.mp4` |
| 9 | 播放页 | `renders/player.html` |

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
--skip-download        复用已下载的视频
--reset-asr            强制重新转写
```

环境变量 `GITHUB_TOKEN` 有值时，会用 API 抽内容（避免 403 和 clone 超时）。

## 单独跑某一步

```bash
# 重新配音（改完 copy.json 后）
python tools/tts.py <工程>

# 重新渲染画面
python engine/render.py <工程>

# 只渲一段验证
python engine/render.py <工程> --clip 0 12

# 抽几帧看
python engine/render.py <工程> --stills 2.0 10.5 20.0

# 确定性检查
python engine/render.py <工程> --det

# 12 格总览图
python engine/render.py <工程> --sheet 12

# 重新混音
python tools/mix.py <工程> --vo1 0.6 --vo2 21.1 \
  --bg 0.06 --music-gain 0.075 --music audio/bgm/Carefree.mp3 \
  --vo-gain 2.0 --lufs -13

# 生成播放页
python tools/make-player-html.py <工程>/renders/final.mp4 \
  -o <工程>/renders/player.html
```

## content.json

`film.js` 只读这个文件。字段缺了对应那张卡就跳过，不报错。

```json
{
  "repo": "owner/name",
  "namePlain": "显示名",
  "emoji": "🎬",
  "headline": "一句话卖点（40 字内）",
  "tagline": "更长一点的描述（60 字内）",
  "version": "1.0.0",
  "accent": "#E8613C",
  "accent2": "#6FE04A",
  "stats": { "star": 129, "fork": 7 },
  "statLabels": { "star": "Star", "fork": "Fork" },
  "features": [
    { "title": "特性名", "desc": "补充说明" }
  ],
  "chapters": [
    { "no": "01", "title": "章节标题" }
  ],
  "palettes": ["色名一", "色名二"],
  "conclusion": ["完全开源", "拿来就用", "三分钟上手"],
  "listTitle": "四步做完一条片子"
}
```

七张卡分别读：

| 卡 | 读哪些字段 |
|---|---|
| 1 封面 | `emoji` `namePlain` `headline` `tagline` `stats` `version` |
| 2 数字墙 | `stats` 里的数字字段 + `statLabels` |
| 3 截图 | `assets/repo.png` |
| 4 特性 | `features`（前 4 条） |
| 5 亮点 | `stats` 里最大的数字 |
| 6 清单 | `chapters` / `palettes` / `items` |
| 7 结论 | `conclusion`（前 3 条） |

## audio/copy.json

```json
{
  "voice": "zh-CN-YunxiNeural",
  "rate": "+45%",
  "pitch": "+5Hz",
  "vo1_at": 0.6,
  "vo2_at": 21.1,
  "vo1": "第一段（约 20 秒，110-130 字）",
  "vo2": "第二段（约 10 秒，60-80 字）",
  "variants": {
    "template": { "vo1": "...", "vo2": "..." },
    "reference": { "vo1": "...", "vo2": "..." }
  },
  "chosen": "template"
}
```

- `vo1` / `vo2` 是最终采用的文案，`tts.py` 只读这两个
- `variants` 里留着两档供对比，不参与生成
- `vo1_at` / `vo2_at` 决定配音在时间轴上的起点

改完重跑 `python tools/tts.py <工程>`，字幕时间轴自动跟着变。

## 时间轴

`film.js` 里的 `T` 对象：

```js
const T = {
  head: 0.15,   // 标题入场
  c1: 1.15,     // 第一张卡开始
  c2: 2.00,
  ...
  outro: 31.4,  // 结尾淡出
};
```

`SUBS` 是字幕表，从 `audio/subs.json` 抄过来（或直接 `window.SUBS` 加载）。

**卡片时间轴要和字幕对齐**，否则会出现「念到第三句，画面还在第一张卡」。

## 配色

`film.js` 里的 `C` 对象：

```js
const C = {
  bg: '#0B0D11',      // 背景
  card: '#F4F1EC',    // 卡片底色
  ink: '#23262B',     // 主文字
  ink2: '#4A5058',    // 次文字
  mute: '#8A8F98',    // 弱化文字
  accent: '#E8613C',  // 主色
  accent2: '#6FE04A', // 副色
  gold: '#C9A227',
  amber: '#E0A458',
};
```

改配色最容易踩的坑：**别让 `ink` 和 `card` 的对比度低于 4.5:1**，手机上会糊。

## 配乐

`audio/bgm/` 里 6 首 Kevin MacLeod（CC BY 4.0）：

| 曲目 | BPM | 适合 |
|---|---|---|
| Carefree（默认） | 100 | 轻快知识类 |
| Life of Riley | 50 | 稳一点 |
| Fluffing a Duck | 60 | 俏皮 |
| Monkeys Spinning Monkeys | 71 | 梗曲 |
| Sneaky Snitch | 22 | 悬疑 |
| Wallpaper | 40 | 最安静 |

换曲后可能要调 `--music-gain`。默认 0.075，对应人声领先 19.2dB。
