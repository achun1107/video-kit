---
name: Bug 报告
about: 跑不通、渲不出来、画面不对
title: '[bug] '
labels: bug
---

## 你跑了什么

```bash
# 贴完整命令
node tools/make-video.mjs --repo ...
```

## 预期 vs 实际

**预期**：

**实际**：

## 报错原文

```
# 贴文字，别截图
```

## 环境

- OS：
- Node：`node -v`
- Python：`python -V`
- ffmpeg：`ffmpeg -version | head -1`
- 有没有跑过 `python engine/get_fonts.py`：

## 如果是画面问题

跑一下抽帧，把出问题的帧贴上来：

```bash
python engine/render.py <工程目录> --stills 2.0 6.0 10.0
```

帧在 `review/` 下。

## `--det` 结果

```bash
python engine/render.py <工程目录> --det
```

输出：
