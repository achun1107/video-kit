/* 风格 D：产品发布页（参考 weitu / 喂兔）
 *
 * 原视频只有 9.47 秒，但它不是录屏 —— 是一张精心设计的「产品发布页」动效：
 *   · 深蓝渐变背景（科技感）
 *   · 顶部胶囊标签「开源项目」（原来写「开源新作」，但这仓库 4 个月前就在更新）
 *   · 超大白色标题
 *   · 蓝色渐变副标题（含 star 数，数字会滚动）
 *   · 灰色一行说明（三个卖点用 · 分隔）
 *   · 中间 macOS 风格窗口卡片（红黄绿三点 + 标题栏 + 代码块）
 *   · 底部两三个特性小卡（图标 + 标题 + 说明 + 标签）
 *
 * 这是四套里最"正式"的一套，适合讲工具类项目。
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const REPO = CT.repo || '';
const VER = CT.version || '';

const DUR = 34.8;

/* 深蓝科技色 */
const BG_TOP = '#0A1628';
const BG_BOT = '#122033';
const WHITE = '#FFFFFF';
const BLUE = '#4A9EFF';
const BLUE2 = '#2E6FF2';
const GRAY = '#8BA0B8';
const CARD = '#1B2A3E';
const CODE_BG = '#0F1926';

const T = {
  c1: 0, c2: 6.0, c3: 12.0, c4: 18.0, c5: 24.0, c6: 29.5,
  outro: DUR - 2.0,
};

const SUBS = window.SUBS || [];

/* 本套的关注引导话术 */
const CTA_TEXT = '关注我，第一时间看到新开源';

const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

/* 顶部胶囊标签 */
function pill(fr, text, y, a) {
  if (a <= 0.003) return;
  const size = 26;
  const w = fr.measure(text, { font: 'sans', size }) + 64;
  const h = 56;
  fr.rect(W / 2 - w / 2, y - h / 2, w, h, { r: 28, fill: WHITE, a: a * 0.10 });
  fr.rect(W / 2 - w / 2, y - h / 2, w, h, { r: 28, stroke: WHITE, strokeW: 1.5, a: a * 0.25 });
  fr.text(text, W / 2, y, { font: 'sans', size, color: '#C8D8E8', a });
}

/* 渐变副标题（蓝→青） */
function gradText(fr, text, y, size, a) {
  if (a <= 0.003) return;
  const ctx = fr.x;
  const tw = fr.measure(text, { font: 'sans', size });
  const g = ctx.createLinearGradient(W / 2 - tw / 2, 0, W / 2 + tw / 2, 0);
  g.addColorStop(0, BLUE);
  g.addColorStop(1, '#5FE8C8');
  ctx.save();
  ctx.globalAlpha = a;
  ctx.font = `700 ${size}px "VK Sans", sans-serif`;
  ctx.fillStyle = g;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, W / 2, y);
  ctx.restore();
}

/* macOS 风格窗口卡片 */
function macWindow(fr, x, y, w, h, a, o) {
  o = o || {};
  if (a <= 0.003) return;

  // 窗口体
  fr.rect(x, y, w, h, { r: 14, fill: CARD, a: a * 0.96 });
  fr.rect(x, y, w, h, { r: 14, stroke: '#2E4258', strokeW: 1.5, a });

  // 标题栏
  const tb = 46;
  fr.rect(x, y, w, tb, { r: 14, fill: '#243548', a: a * 0.9 });
  fr.rect(x, y + tb - 14, w, 14, { fill: '#243548', a: a * 0.9 });

  // 红黄绿三点
  const dots = ['#FF5F57', '#FEBC2E', '#28C840'];
  dots.forEach((c, i) => {
    fr.rect(x + 20 + i * 24, y + tb / 2 - 7, 14, 14, { r: 7, fill: c, a: a * 0.95 });
  });

  // 标题栏文字
  if (o.title) {
    fr.text(o.title, x + w / 2, y + tb / 2, {
      font: 'mono', size: 20, color: GRAY, a: a * 0.9,
    });
  }
}

/* 代码块（带 $ 提示符和语法色） */
function codeBlock(fr, x, y, w, h, lines, a) {
  if (a <= 0.003) return;
  fr.rect(x, y, w, h, { r: 8, fill: CODE_BG, a: a * 0.98 });

  lines.forEach((ln, i) => {
    const a2 = ss(a, 0.3 + i * 0.15, 1.0);
    if (a2 <= 0.003) return;
    const yy = y + 26 + i * 34;
    if (ln[0] === '$') {
      fr.text('$', x + 20, yy, { font: 'mono', size: 20, color: '#5FE8C8', a: a2, align: 'l' });
      fr.text(ln.slice(1).trim(), x + 44, yy, { font: 'mono', size: 20, color: '#D8E4F0', a: a2, align: 'l' });
    } else if (ln.trim().startsWith('//')) {
      fr.text(ln, x + 20, yy, { font: 'mono', size: 18, color: '#4A6078', a: a2, align: 'l' });
    } else {
      fr.text(ln, x + 20, yy, { font: 'mono', size: 18, color: '#8BA0B8', a: a2, align: 'l' });
    }
  });
}

/* 底部特性小卡 */
function featureCard(fr, x, y, w, h, title, desc, tag, a, col) {
  if (a <= 0.003) return;
  fr.rect(x, y, w, h, { r: 12, fill: CARD, a: a * 0.9 });
  fr.rect(x, y, w, h, { r: 12, stroke: '#2E4258', strokeW: 1.2, a: a * 0.7 });

  // 左上角小图标（圆角方块 + 符号）
  fr.rect(x + 20, y + 20, 40, 40, { r: 10, fill: col || BLUE, a: a * 0.18 });
  fr.text('◆', x + 40, y + 40, { font: 'sans', size: 20, color: col || BLUE, a: a * 0.9 });

  // 标签（右上角）
  if (tag) {
    const tw = fr.measure(tag, { font: 'sans', size: 16 }) + 20;
    fr.rect(x + w - tw - 16, y + 22, tw, 28, { r: 14, fill: col || BLUE, a: a * 0.16 });
    fr.text(tag, x + w - tw / 2 - 16, y + 36, { font: 'sans', size: 16, color: col || BLUE, a });
  }

  // 字号按字数直接算（fr.measure 在这里不准，量出来偏小导致溢出）
  const nch = Array.from(title).length;
  const tsize = Math.max(16, Math.min(30, Math.floor((w - 44) / Math.max(nch, 1))));
  fr.text(title, x + 20, y + 92, { font: 'sans', size: tsize, color: WHITE, a, align: 'l' });
  if (desc) {
    fr.text(desc.slice(0, 14), x + 20, y + 134, { font: 'sans', size: 19, color: GRAY, a, align: 'l' });
  }
}

/* ---------- 1 标题页 ---------- */
/* 标题分行：只在模块加载时算一次。
 *
 * 原来写在 card1() 里，每帧都跑一遍 measure（1044 帧 × 15 字 = 1.5 万次），
 * measure 每次都要重设 canvas.font，直接导致渲染 180 秒超时。
 * 标题内容在渲染期不变，没必要每帧重算。 */
const HEAD_LINES = (() => {
  const raw = HEAD || NAME;
  const out = [];
  let cur = '';
  let w = 0;
  // 88px 黑体下中文约 1 字宽 = 88，英文约 0.55
  const maxW = W * 0.88;
  for (const ch of Array.from(raw)) {
    const cw = /[\u4e00-\u9fff]/.test(ch) ? 88 : (ch === ' ' ? 24 : 49);
    if (w + cw > maxW && cur) {
      out.push(cur);
      cur = ch;
      w = cw;
    } else {
      cur += ch;
      w += cw;
    }
  }
  if (cur) out.push(cur);
  return out.slice(0, 2);
})();

/* ---------- 1 标题页 ---------- */
function card1(fr, lt) {
  // 入场动画：标题逐行滑入，star 和说明依次补上。
  // 原来是全 a:1，前 2 秒画面变化只有 1.6% —— 抖音上等于静止。
  const t01 = (a, b) => Math.max(0, Math.min(1, (lt - a) / (b - a)));
  const ease = x => 1 - Math.pow(1 - x, 3);

  const pp = ease(t01(0, 0.35));
  pill(fr, '开源项目', 300, pp);   // 项目 4 个月前就在更新，不叫新作

  const use = HEAD_LINES;
  use.forEach((ln, i) => {
    // 第一行从 0 秒起、alpha 0.65 起步 —— 否则 0.1 秒时画面 90% 是空的深蓝，
    // preflight 的 D 项只测到 0.4% 亮点。
    const pi = i === 0
      ? 0.65 + 0.35 * ease(t01(0.0, 0.5))
      : ease(t01(0.10 + i * 0.12, 0.55 + i * 0.12));
    if (pi <= 0.003) return;
    fr.text(ln, W / 2, 440 + i * 108 + 32 * (1 - pi), {
      font: 'sans', size: 88, color: WHITE, a: pi,
    });
  });

  // 副标题：等标题落定再出
  const star = STATS.star;
  const subY = 440 + use.length * 108 + 30;
  const ps = ease(t01(0.55, 0.95));
  if (star && ps > 0.003) {
    gradText(fr, `GitHub ${star.toLocaleString('en-US')}+ ★`, subY, 52, ps);
  }

  // 一行说明：最后出
  const tags = FEATURES.slice(0, 3).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')).slice(0, 8));
  const line = tags.length ? tags.join(' · ') : '结构化 JSON · 稳定标识 · 毫秒级';
  const pl = ease(t01(0.75, 1.15));
  if (pl > 0.003) {
    fr.text(line, W / 2, subY + 90, {
      font: 'sans', size: 26, color: GRAY, a: pl,
    });
  }
}

/* ---------- 2 GitHub 卡片 ---------- */
function card2(fr, lt) {
  const a = ss(lt, 0.1, 0.9);
  const w = 980, h = 560, x = (W - w) / 2, y = 360;

  macWindow(fr, x, y, w, h, a, { title: '开源仓库' });

  // 卡内：项目名 + star + 特性勾选
  const a2 = ss(lt, 0.6, 1.6);
  fr.text(NAME, x + 44, y + 120, { font: 'sans', size: 46, color: WHITE, a: a2, align: 'l' });
  if (HEAD) {
    fr.text(HEAD.slice(0, 16), x + 44, y + 178, {
      font: 'sans', size: 24, color: GRAY, a: a2, align: 'l',
    });
  }

  const star = STATS.star;
  if (star) {
    const a3 = ss(lt, 1.2, 2.0);
    fr.text(`${star.toLocaleString('en-US')} ★`, x + 44, y + 250, {
      font: 'mono', size: 34, color: BLUE, a: a3, align: 'l',
    });
  }

  // 两列勾选
  const list = FEATURES.slice(0, 4).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')).slice(0, 10));
  const use = list.length ? list : ['结构化 JSON', '稳定标识', '跨平台', '后台静默'];
  use.forEach((t, i) => {
    const a4 = ss(lt, 1.6 + i * 0.15, 2.2 + i * 0.15);
    if (a4 <= 0.003) return;
    const c = i % 2, r = Math.floor(i / 2);
    const tx = x + 44 + c * 380, ty = y + 320 + r * 46;
    fr.text('✓', tx, ty, { font: 'sans', size: 22, color: '#5FE8C8', a: a4, align: 'l' });
    fr.text(t, tx + 30, ty, { font: 'sans', size: 22, color: '#C8D8E8', a: a4, align: 'l' });
  });
}

/* ---------- 3 代码示例 ---------- */
function card3(fr, lt) {
  // 不再画假代码块 —— 原来那两段 `$ tool snapshot` 是 Agent Desktop 的，
  // 小百看板没有 CLI。观众搜不到会取关。
  const a = 1;
  const w = 980, h = 560, x = (W - w) / 2, y = 360;

  macWindow(fr, x, y, w, h, a, { title: '它能做什么' });

  const list = FEATURES.slice(0, 3).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')));

  list.forEach((t, i2) => {
    const aa = i2 === 0 ? 1 : ss(lt, 0.4 + i2 * 0.5, 0.4 + i2 * 0.5 + 0.9);
    if (aa <= 0.003) return;
    const ty = y + 100 + i2 * 108;

    // 序号
    fr.text('0' + (i2 + 1), x + 48, ty, {
      font: 'mono', size: 26, color: BLUE, a: aa * 0.85, align: 'l',
    });
    // 能力文字（按宽度缩）
    let size = 34;
    while (size > 20 && fr.measure(t, { font: 'sans', size }) > w - 150) size -= 2;
    fr.text(t, x + 110, ty, {
      font: 'sans', size, color: '#D8E4F0', a: aa, align: 'l',
    });
    // 分隔线
    fr.rect(x + 48, ty + 34, w - 96, 1, { fill: '#2E4258', a: aa * 0.6 });
  });
}

/* ---------- 4 三个特性小卡 ---------- */
function card4(fr, lt) {
  const list = FEATURES.slice(0, 3);
  const rows = list.length ? list.map(f => {
    const t = (typeof f === 'string') ? f : (f.title || f.name || '');
    const d = (typeof f === 'string') ? '' : (f.desc || f.hint || '');
    return [String(t), String(d)];   // 不截断，featureCard 里字号会自适应
  }) : [['不看图', '直接读系统树'], ['稳定标识', '不会点歪'], ['毫秒级', '快速响应']];

  const gap = 24, w = (W - 120 - gap * (rows.length - 1)) / rows.length;
  rows.forEach((r, i) => {
    const a = ss(lt, 0.3 + i * 0.35, 0.3 + i * 0.35 + 0.9);
    if (a <= 0.003) return;
    const x = 60 + i * (w + gap);
    const y = 700 + (1 - a) * 40;
    const cols = [BLUE, '#5FE8C8', '#C8A8FF'];
    featureCard(fr, x, y, w, 230, r[0], r[1], i === 0 ? '毫秒级' : '', a, cols[i % 3]);
  });
}

/* ---------- 5 star 大数字 ---------- */
function card5(fr, lt) {
  const star = STATS.star;
  const a = ss(lt, 0.1, 1.0);
  pill(fr, '开源项目', 340, a);

  if (!star) {
    fr.text('完全开源', W / 2, 620, { font: 'sans', size: 110, color: WHITE, a: ss(lt, 0.3, 1.5) });
    return;
  }
  const k = ss(lt, 0.3, 2.0);
  const shown = Math.round(star * E.out3(k));
  fr.text(shown.toLocaleString('en-US'), W / 2, 640, {
    font: 'sans', size: 230, color: WHITE, a: Math.min(1, k * 1.8),
  });
  gradText(fr, '★ GitHub Stars', 800, 48, ss(lt, 1.2, 2.0));
}

/* ---------- 6 结论 ---------- */
function card6(fr, lt) {
  const concl = (CT.conclusion || ['完全开源', '拿来就用', '三分钟上手']).slice(0, 3);
  concl.forEach((t, i) => {
    const a = ss(lt, 0.3 + i * 0.6, 0.3 + i * 0.6 + 1.0);
    if (a <= 0.003) return;
    fr.text(String(t).slice(0, 12), W / 2, 620 + i * 130, {
      font: 'sans', size: 72, color: i === concl.length - 1 ? BLUE : WHITE, a,
    });
  });

  if (REPO) {
    fr.text(REPO, W / 2, 1180, {
      font: 'mono', size: 26, color: GRAY, a: ss(lt, 2.0, 2.7),
    });
  }
  fr.text('' /* 原来写「支持 macOS · Windows · Linux」，那是别的项目的 */, W / 2, 1250, {
    font: 'sans', size: 22, color: '#4A6078', a: ss(lt, 2.2, 2.9),
  });

  // 结尾引导（系列号 + 关注）
  outroBar(fr, 1, { y: 1290 });
}

function subtitles(fr, t) {
  if (!SUBS.length) return;
  const cand = SUBS.filter(x => t >= x.a - 0.05 && t <= x.b + 0.25);
  const s = cand.length ? cand[cand.length - 1] : null;
  if (!s) return;
  const a = ss(t, s.a, s.a + 0.16) * (1 - ss(t, s.b, s.b + 0.1));
  if (a <= 0.003) return;

  const vw = Array.from(s.zh).reduce(
    (n, ch) => n + (/[\u4e00-\u9fff]/.test(ch) ? 1 : (ch === ' ' ? 0.3 : 0.56)), 0);
  const size = Math.min(56, Math.round(640 / (vw * 1.0)));

  fr.text(s.zh, W / 2, 1330, {
    font: 'sans', size, color: WHITE, a: a * 0.95,
    shadow: 0.8, shadowBlur: 10,
  });
}

const CUES = [
  [T.c1, 'rise'], [T.c2, 'soft'], [T.c3, 'tick'],
  [T.c4, 'chord', { root: 0 }], [T.c5, 'skip'], [T.c6, 'chord', { root: 7 }],
  [DUR - 1.2, 'hush'],
];


/* 段切换：进入时缩放冲击 + 上移，不是纯淡入。
 * 人的眼睛对变化敏感，纯淡入在抖音上会被当成静态图划走。 */
function cut(fr, t, a, b, fn) {
  if (t < a || t >= b) return;

  // 硬切：透明度直接 1，不淡入。淡化在抖音上会被当成静态图。
  // 只靠缩放 + 位移制造"变化感"。
  const kin = seg(t, a, Math.min(a + 0.30, b));
  const e = E.out3(kin);
  const s = 1 + 0.09 * (1 - e);         // 1.09 → 1.0
  const dy = 38 * (1 - e);              // 下 38px → 0

  // 退出只留 0.05 秒淡出（切走时不硬切，避免闪）
  const kout = seg(t, b - 0.05, b);
  const kk = 1 - kout;

  // 围绕画面中心缩放：canvas 是 translate→scale，中心不动需要 dx = cx*(1-s)
  fr.g({
    a: kk, s,
    at: [W / 2 * (1 - s), H / 2 * (1 - s) + dy],
  }, () => fn(fr, t - a));
}


/* 结尾引导：系列号 + 关注 CTA。
 * 抖音观众不会主动关注，必须明说 —— 这是运营的基本动作。 */
function outroBar(fr, a, o) {
  o = o || {};
  if (a <= 0.003) return;
  const y = o.y || 1290;
  const color = o.color || '#9A9A9A';
  const accent = o.accent || '#FFE500';

  // 深色底带：CTA 压在截图上会跟内容混在一起，必须托出来
  // 渐变压暗：从 y-90 一路压到画面底部。
  // 不做成固定高度的横带 —— 那样会像贴了一条黑胶布，上下都露出截图。
  const _g = fr.x.createLinearGradient(0, y - 90, 0, H);
  _g.addColorStop(0, 'rgba(0,0,0,0)');
  _g.addColorStop(0.34, 'rgba(0,0,0,0.88)');
  _g.addColorStop(1, 'rgba(0,0,0,0.95)');
  fr.x.save();
  fr.x.globalAlpha *= a;
  fr.x.fillStyle = _g;
  fr.x.fillRect(0, y - 90, W, H - (y - 90));
  fr.x.restore();

  // 系列号
  const series = (CT.series || 0);
  if (series) {
    fr.text('第 ' + series + ' 个开源项目', W / 2, y, {
      font: 'mono', size: 24, color, a: a * 0.8,
    });
  }

  // 分隔线
  fr.rect(W / 2 - 90, y + 34, 180, 1, { fill: color, a: a * 0.4 });

  // CTA
  fr.text(o.cta || CTA_TEXT, W / 2, y + 74, {
    font: 'sans', size: 30, color: accent, a,
  });
}

VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.4 },
  draw(fr, t) {
    fr.look.bgo = { color: BG_TOP };
    fr.look.bloom = 0.06;
    fr.look.grain = 0.03;

    /* 深蓝渐变底 + 顶部径向光 */
    fr.look.under = (ctx, tt) => {
      ctx.save();

      // 渐变本身缓慢流动：三个色标的位置随 t 轻微移动。
      // 第一版只动了光晕（alpha ±0.055），幅度太小，
      // 缩到 216×384 的检测图上被平均值抹平，测不出变化。
      const f1 = 0.55 + 0.10 * Math.sin(tt * Math.PI * 2 / 7.3);
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, BG_TOP);
      g.addColorStop(Math.max(0.25, Math.min(0.8, f1)), BG_BOT);
      g.addColorStop(1, BG_TOP);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      // 顶部蓝光：横向漂移 + 强度呼吸 + 半径脉动（幅度加大）
      const lx = W / 2 + Math.sin(tt * Math.PI * 2 / 6.5) * W * 0.34;
      const lw = 0.16 + 0.12 * Math.sin(tt * Math.PI * 2 / 4.2);
      const lr = W * (0.95 + 0.22 * Math.sin(tt * Math.PI * 2 / 5.3));
      const r = ctx.createRadialGradient(lx, 0, 0, lx, 0, lr);
      r.addColorStop(0, `rgba(74,158,255,${Math.max(0, lw).toFixed(4)})`);
      r.addColorStop(1, 'rgba(74,158,255,0)');
      ctx.fillStyle = r;
      ctx.fillRect(0, 0, W, 900);

      // 底部青色余光，和顶部反相摆动
      const bx = W / 2 - Math.sin(tt * Math.PI * 2 / 8.1) * W * 0.30;
      const bw = 0.10 + 0.09 * Math.sin(tt * Math.PI * 2 / 5.7 + 1.6);
      const br = ctx.createRadialGradient(bx, H, 0, bx, H, W * 1.05);
      br.addColorStop(0, `rgba(60,220,200,${Math.max(0, bw).toFixed(4)})`);
      br.addColorStop(1, 'rgba(60,220,200,0)');
      ctx.fillStyle = br;
      ctx.fillRect(0, H - 1100, W, 1100);

      // 底部青光
      const r2 = ctx.createRadialGradient(W / 2, H, 0, W / 2, H, W * 0.7);
      r2.addColorStop(0, 'rgba(95,232,200,0.06)');
      r2.addColorStop(1, 'rgba(95,232,200,0)');
      ctx.fillStyle = r2;
      ctx.fillRect(0, H - 800, W, 800);
      ctx.restore();
    };

    const segs = [
      [T.c1, T.c2, card1], [T.c2, T.c3, card2], [T.c3, T.c4, card3],
      [T.c4, T.c5, card4], [T.c5, T.c6, card5], [T.c6, DUR, card6],
    ];

    segs.forEach(sg => cut(fr, t, sg[0], sg[1], sg[2]));

    subtitles(fr, t);

    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    fr.text(timecode(t), W - 40, H - 34, {
      font: 'mono', size: 16, color: '#2A3A50',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'r',
    });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
