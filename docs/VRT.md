# 视觉回归测试

改完画面代码，跑一次比对，看有没有把别的卡碰坏。

```bash
python engine/get_fonts.py      # 第一次要下字体，43MB
python tests/vrt.py             # 比对
python tests/vrt.py --update    # 重建基准（改动是有意的时候）
```

## 它做什么

渲染一个固定的 fixture 工程（`tests/fixture/`）的 9 帧，和 `tests/baseline/` 里的基准帧比对：

| 帧 | 时间 | 验什么 |
|---|---|---|
| card1_cover | 2.0s | 封面：标题、emoji、标签 |
| card2_stats | 5.0s | 数字墙 |
| card3_shot | 9.5s | GitHub 截图卡 |
| card4_features | 12.0s | 特性列表 |
| card5_highlight | 16.0s | 亮点大数字 |
| card6_list | 19.5s | 清单 |
| card7_conclusion | 24.0s | 结论 |
| subtitle | 6.5s | 字幕位置与字号 |
| end | 30.0s | 尾部过渡 |

比的是 **MAE（平均绝对误差）**，不是逐像素相等——后者太脆。
两张图都缩到 360×640 后逐像素求差，默认阈值 `0.02`（2%）。

## 为什么基准帧不能当"绝对真值"

**字体渲染跨平台不一致**：Windows 用 DirectWrite，Linux 用 FreeType，macOS 用 CoreText。
同一份代码渲出来像素必有差异。

所以基准只在**同一个环境**里当回归检测用：

- 本机改完代码 → 跑比对 → 看画面有没有被意外改动
- 换机器 / 换字体版本 → `--update` 重建基准

**这也是为什么不在 CI 里跑。** 跨 runner 的字体差异会让比对一直红，信噪比为零。
CI 只跑结构检查（语法、测试、仓库卫生、密钥扫描）。

## 输出长什么样

```
=== 比对（阈值 0.020）===
渲染 9 帧 …

  ✓ card1_cover          MAE 0.0000
  ✓ card2_stats          MAE 0.0000
  ✓ card3_shot           MAE 0.0000
  ✗ card4_features       MAE 0.0413  ███████████████████
  ...

✗ 1 帧超出阈值
  最大差异：card4_features  MAE 0.0413
  差异图：tests/.vrt-diff

  如果改动是有意的：python tests/vrt.py --update
  如果是意外的：查 tools/film-template.js 或 engine/
```

差异图在 `tests/.vrt-diff/`，变红的地方是改动处（差异放大 4 倍，人眼能看见）。

## 参数

```
--update          重建基准帧
--threshold N     容差，默认 0.02
--keep            保留临时渲染产物（tests/.vrt-work）
--skip-mem-check  跳过内存预检
```

## 内存要求

渲染要 **至少 2.5 GB 可用内存**。不够会卡在 `window.READY` 上等 180 秒才超时，
报错信息还看不出是内存问题。所以脚本开头会预检，不够就直接说：

```
⚠ 可用内存只有 1.8 GB，渲染至少要 2.5 GB
  Playwright 起 headless Chrome + 加载 43MB 字体，内存不够会卡在
  window.READY 上等 180 秒。关掉一些浏览器标签页再试。
```

## 什么时候该 `--update`

对：

- 有意调整了卡片布局、字号、配色
- 换了 `film-template.js` 的视觉参数
- 升级了字体版本

不对：

- 只改了 `README`、测试、文档
- 只改了 `make-video.mjs` 的流程（不影响画面）
- 只加了新的 `content.json` 字段（fixture 里没用到）

**判据**：如果你能用一句话说清"画面为什么该变"，就 `--update`；
说不清就说明碰坏了，去查。

## 基准帧有多大

9 帧 360×640 PNG，合计 **836 KB**。放仓库里不算负担，而且比每次重渲便宜。

## 已知限制

1. **只覆盖 fixture 的数据** — 真实项目的 `content.json` 字段组合更多
   （比如特性列表 0 条、`conclusion` 只有 2 项），那些分支没比对
2. **不验动态部分** — 粒子、流光是 `t` 的连续函数，抽帧只能验几个时间点
3. **不比字幕文字内容** — 只比位置和字号，文本对不对是 `tts.py` 的测试管的
4. **阈值是经验值** — 0.02 大概等于"看得出来但不一定算错"的程度，
   调太严会因为字体微调频繁误报
