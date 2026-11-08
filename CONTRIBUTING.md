# 参与贡献

先说清楚：**这个项目是为一个人的工作流量身做的**，不是通用框架。
所以接受 PR 的标准不是「功能好不好」，而是「会不会破坏现有流程的确定性」。

## 什么样的 PR 会合

- 修 bug（尤其是 `--det` 不过、渲染报错、平台兼容）
- 补文档（README 说错了、示例跑不通、FAQ 缺常见坑）
- 加新的输入源（参考 `--douyin` 那块的结构）
- 加新的卡片类型（不改动已有七张卡的前提下）
- 性能优化（渲染更快、内存更省），前提是 `--det` 仍然通过

## 什么样的 PR 不会合

- 换技术栈（比如把 Python 渲染换成 Rust）
- 加运行时依赖到 `engine/vk.js`（它的卖点就是零依赖）
- 破坏 `--det` 确定性的「优化」
- 只改措辞、调格式的纯风格 PR
- 把 `content.json` 的字段改名（会让所有人已有的 `film.js` 全废）

## 开发流程

```bash
git clone https://github.com/achun1107/video-kit
cd video-kit

python engine/get_fonts.py
pip install playwright edge-tts numpy scipy pillow faster-whisper jieba
python -m playwright install chrome
```

改完必须验：

```bash
# 抽几帧看画面
python engine/render.py <工程目录> --stills 2.0 6.0 10.0

# 确定性检查 —— 必须输出 deterministic
python engine/render.py <工程目录> --det
```

**`--det` 不过的 PR 直接关**，不管功能多好。这条没得商量：
画面不可复现，前面所有「改一行重渲」的工作流就全废了。

## 代码规范

- Python：4 空格，snake_case，不强制类型标注
- JavaScript：2 空格，`const` 优先
- 注释写「为什么」，不写「做什么」
- 错误信息用中文，前缀 `×`

## 提交信息

```
<type>: <一句话说清改了什么>

<为什么这么改。如果踩过坑，把坑写出来。>
```

`type` 用 `feat` / `fix` / `docs` / `chore` / `refactor`。

好的例子：

```
fix: index.html 补上 content.js 和 VK_SIZE

生成的 index.html 缺这两个东西，表现为卡片里全是灰色占位条、
画幅变成 16:9。根因是模板从 engine/index.html 复制，那份是横屏的。
现在改用 tools/index.template.html。
```

不好的例子：

```
update files
```

## 报告问题

开 issue 时带上：

- 你跑的完整命令
- 报错原文（别截图，贴文字）
- Node / Python / ffmpeg 版本
- 如果画面有问题，贴一张 `--stills` 出来的帧

## 授权

你的贡献按 MIT 授权（见 [LICENSE](LICENSE)）。
