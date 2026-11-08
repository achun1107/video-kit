# 安全策略

## 报告漏洞

**不要开公开 issue。** 用 GitHub 的私密报告：

https://github.com/achun1107/video-kit/security/advisories/new

或者邮件：在 commit 里找作者邮箱（不写在这里，避免被爬虫抓）。

请包含：

- 复现步骤
- 影响范围（能读到什么、能执行什么）
- 你的环境（OS / Node / Python 版本）

一般 72 小时内回复。

## 支持范围

只维护最新 release 的次版本线。旧版本除非影响面很大，不然不回补。

## 这个项目会碰到什么

video-kit 跑起来会做这些事，你得知道：

| 行为 | 说明 |
|---|---|
| **执行 ffmpeg / ffprobe** | 处理你自己指定的媒体文件 |
| **启动 Playwright 浏览器** | 截 GitHub 页面、抓抖音页面 |
| **发起 HTTP 请求** | `api.github.com`、`raw.githubusercontent.com`、`douyin.com`、`v.douyin.com` |
| **写临时文件** | `renders/`、`review/`、`_repos/`、系统临时目录 |
| **调用 edge-tts** | 把文案发到微软的 TTS 服务（联网） |

### 它不会做的事

- 不读取 `~/.ssh`、`~/.aws`、浏览器 cookie 库等无关凭据
- 不上传你的文案、视频、仓库内容到本项目作者的服务器（作者没有服务器）
- 不执行仓库里的代码（`extract-content.mjs` 只读文本文件，不 `require` 被抽的仓库）

### 需要注意的

**`GITHUB_TOKEN`**：环境变量里的 token 会被用于调 GitHub API，也会作为参数传给子进程
（`repo-content.py --token`）。在多用户机器上留意进程列表可见性。

**抖音 cookie**：`douyin-download.py` 用 Playwright 自己拿 cookie 存到
`douyin/dl/cookies.txt`，这个文件含你的抖音会话标识。已在 `.gitignore` 里，
但如果你把 `douyin/` 整个目录拷给别人，等于把会话给出去。

**渲染的仓库内容**：`--repo` 指向的仓库 README 会被读进来做文案素材。如果你处理的是
包含敏感信息的私有文档，注意它可能出现在成片里。

## 依赖

- Node 侧无运行时依赖（`tools/*.mjs` 全是标准库）
- Python 侧：`playwright`、`edge-tts`、`faster-whisper`、`jieba`、`numpy`、`scipy`、`pillow`
- 系统：`ffmpeg`、`ffprobe`

定期跑 `pip list --outdated` 和 `npm audit`（本项目没有 npm 依赖，跑一下也没坏处）。
