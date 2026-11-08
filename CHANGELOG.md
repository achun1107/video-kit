# 变更记录

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-11-08

首个可用版本。

### 新增

- **九步流水线**：`tools/make-video.mjs` 一条命令从仓库/抖音链接跑到成片
  - 铺引擎骨架 → 仓库就位 → 抽内容 → 截图 → 配音 → 字幕 → 铺模板 → 渲染 → 混音 → 播放页
- **通用七卡模板** `tools/film-template.js`：只读 `window.CONTENT`，不写死项目信息
  - 封面 / 数字墙 / GitHub 截图 / 特性列表 / 亮点数字 / 清单 / 结论
- **两种输入**
  - `--repo`：GitHub 仓库地址或本地目录
  - `--douyin`：抖音分享链接（视频分享和主页分享都支持）
- **抖音链路**
  - `tools/douyin-rank.py` 抓主页视频列表，带点赞数，按赞降序
  - `tools/douyin-download.py` 从页面提取 mp4 直链（绕过 yt-dlp 的 cookie 限制）
  - `tools/transcribe-local.py` faster-whisper 本地转写
  - `tools/repo-finder.py` 从转写反查仓库（star 指纹 + jieba 关键词 + 置信度门槛）
  - `tools/asrfix.py` whisper 中文误听纠正表（Gatehub→GitHub、紫围斗树→紫微斗数 等）
  - `tools/reverse-batch.py` 批量逆向高赞视频
- **两档文案** `tools/script-writer.py`
  - 模板稿：只读 `content.json`，套固定骨架
  - 参考稿：借原视频转写结构和节奏，换主语
- **渲染引擎** `engine/vk.js`：每帧是 `t` 的纯函数，支持 `--stills` / `--det` / `--sheet` / `--clip`
- **三层混音** `tools/mix.py`：人声 / 音效 / 配乐，人声领先 19.2dB，`loudnorm -13 LUFS`
- **自包含播放页** `tools/make-player-html.py`：base64 内嵌视频，单文件可直接播

### 已知限制

- 文案必须人写，自动生成的是通用模板稿
- 私有仓库不支持
- 渲染 3–6 分钟（1044 帧）
- `bin/xianyu.js` 类的工作流骨架不适用本项目（那是另一个仓库的事）

### 修正过的坑

记录下来免得后人重踩：

- `ctx.shadow*` 会破坏 `--det` 确定性 → 改用半透明矩形模拟阴影
- 单帧 `drawImage` 超过 3 次带变换会破坏确定性 → 先烤到离屏 canvas
- `index.html` 缺 `content.js` 和 `window.VK_SIZE` → 卡片空白 + 画幅变 16:9
- `edge-tts` 的 `rate` 必须是 `+45%` 不是 `+45`
- 循环 `replace` 纠正误听会叠字（`HyperFrames` → `HyperFramess`）→ 改成一次性正则替换
- 中文按滑窗切词会切出「紫微斗数的开」这种碎片 → 用 jieba TF-IDF
- 口播里的 star 数会过时（1.05万 → 实际 1.67万）→ 匹配上限放到 2 倍

---

## 版本说明

- **主版本**：`content.json` 字段变更、CLI 参数不兼容
- **次版本**：新增输入源、新增卡片类型、新增工具
- **修订号**：修 bug、改文案、调参数
