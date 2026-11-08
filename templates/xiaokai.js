/* 风格 C：网格排版（参考 xiaokai / AI小凯）
 *
 * 特征：
 *   · 黑色网格背景（参考视频最显著的识别特征）
 *   · 白底/黑底卡片式大字标题，斜切
 *   · 网页截图贴上去，用半透明色块高亮重点
 *   · 白色标签条叠加说明
 *   · 手绘小元素（参考视频里有个 "SO EASY" 简笔画）
 *   · 局部放大推拉
 *
 * 节奏：卡片进 → 截图进 → 高亮扫过 → 标签压上
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const REPO = CT.repo || '';

const DUR = 34.8;

const BG = '#0B0B0B';
const GRID = '#1E1E1E';
const WHITE = '#FFFFFF';
const HILITE = '#7CE87C';   // 参考视频的荧光绿

const T = {
  c1: 0, c2: 6.0, c3: 11.5, c4: 17.0, c5: 22.5, c6: 28.0,
  outro: DUR - 2.0,
};

const SUBS = window.SUBS || [];

const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

/* 黑色网格背景 —— 参考视频最醒目的特征 */
function drawGrid(ctx) {
  const step = 90;
  ctx.save();
  ctx.strokeStyle = GRID;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let x = 0; x <= W; x += step) {
    ctx.moveTo(x, 0);
    ctx.lineTo(x, H);
  }
  for (let y = 0; y <= H; y += step) {
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
  }
  ctx.stroke();
  ctx.restore();
}

/* 白底卡片标题（参考视频第一帧：「【一天一个神奇网站】资源爬取神器」）*/
function titleCard(fr, text, y, a, o) {
  o = o || {};
  if (a <= 0.003) return;
  const lines = Array.isArray(text) ? text : [text];
  const pad = 44;
  const size = o.size || 76;
  const lh = size * 1.32;
  const h = lines.length * lh + pad * 2;

  // 量最大宽度
  let maxW = 0;
  for (const l of lines) {
    const w = fr.measure(l, { font: 'sans', size });
    if (w > maxW) maxW = w;
  }
  const bw = Math.min(W - 120, maxW + pad * 2);

  const ctx = fr.x;
  ctx.save();
  ctx.translate(W / 2, y);
  ctx.rotate(o.rot || 0);
  // 白底
  fr.rect(-bw / 2, -h / 2, bw, h, { r: 8, fill: o.bg || WHITE, a });
  // 黑字
  lines.forEach((l, i) => {
    fr.text(l, 0, -h / 2 + pad + lh * (i + 0.5) - size * 0.12, {
      font: 'sans', size, color: o.fg || '#111111', a, align: 'c',
    });
  });
  ctx.restore();
}

/* 白色标签条（参考视频里贴在截图上的说明文字）*/
function tagBar(fr, text, x, y, a, o) {
  o = o || {};
  if (a <= 0.003) return;
  const size = o.size || 34;
  const w = fr.measure(text, { font: 'sans', size }) + 56;
  const h = size + 36;
  fr.rect(x - w / 2, y - h / 2, w, h, { r: 10, fill: '#FFFFFF', a: a * 0.94 });
  fr.text(text, x, y, {
    font: 'sans', size, color: '#111111', a, align: 'c',
  });
}

/* 荧光色块高亮（在截图上扫一段）*/
function swipe(fr, x, y, w, h, k, a) {
  if (k <= 0.003) return;
  const ww = w * Math.min(1, k);
  fr.rect(x - w / 2, y - h / 2, ww, h, { fill: HILITE, a: (a || 1) * 0.32 });
}

/* 截图（带白色边框，像贴在网格上的卡片）*/
function shotCard(fr, img, x, y, w, k, a) {
  if (a <= 0.003) return;
  if (!img || !img.complete || !img.naturalWidth) {
    fr.rect(x, y, w, w * 0.55, { fill: '#1A1A1A', a });
    return;
  }
  const h = w * img.naturalHeight / img.naturalWidth;
  const ctx = fr.x;
  ctx.save();
  ctx.globalAlpha = a;
  // 白边
  fr.rect(x - 6, y - 6, w + 12, h + 12, { r: 6, fill: '#FFFFFF', a: a * 0.9 });
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, 3); else ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
  return h;
}

const IMG = new Image();
IMG.src = 'assets/repo.png';
window.__IMAGES = [IMG];

/* ---------- 1 标题卡 ---------- */
function card1(fr, lt) {
  // 硬切 + star 前置
  const star = STATS.star;
  if (star) {
    fr.text(star.toLocaleString('en-US') + ' ★', W / 2, 340, {
      font: 'sans', size: 110, color: '#FFD400', a: 1, align: 'c',
    });
  }
  titleCard(fr, ['【' + NAME + '】', '开源工具'], 620, 1, { size: 82, rot: -0.02 });
  const k = ss(lt, 0.4, 1.2);
  if (k > 0.003) {
    fr.rect(W / 2 - 240, 760, 480 * k, 8, { fill: '#FFD400', a: 0.9 });
  }
}

/* ---------- 2 截图 + 高亮 ---------- */
function card2(fr, lt) {
  const a = ss(lt, 0.1, 0.9);
  const w = 820, x = (W - w) / 2, y = 420;
  const h = shotCard(fr, IMG, x, y, w, 0, a);

  const k = ss(lt, 0.8, 1.8);
  swipe(fr, W / 2, y + (h || 460) * 0.5, 700, 120, k, a);

  tagBar(fr, '这就是那个开源项目', W / 2, y + (h || 460) + 120, ss(lt, 1.2, 2.0));
}

/* ---------- 3 star ---------- */
function card3(fr, lt) {
  const star = STATS.star;
  const a = ss(lt, 0.2, 1.4);
  if (!star) {
    titleCard(fr, ['完全开源'], 760, a, { size: 96 });
    return;
  }
  const k = ss(lt, 0.2, 1.7);
  const shown = Math.round(star * E.out3(k));
  titleCard(fr, [shown.toLocaleString('en-US'), 'STAR'], 720, Math.min(1, k * 1.5),
            { size: 96, rot: -0.02 });
  tagBar(fr, 'GitHub 上已经爆火', W / 2, 960, ss(lt, 1.2, 2.0));
}

/* ---------- 4 三个特性（参考视频里是竖排大列表）---------- */
function card4(fr, lt) {
  const list = FEATURES.slice(0, 3).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')).slice(0, 10));
  const rows = list.length ? list : ['智能识别', '自动适配', '零配置'];

  rows.forEach((t, i) => {
    const a = ss(lt, 0.3 + i * 0.7, 0.3 + i * 0.7 + 1.0);
    if (a <= 0.003) return;
    const y = 560 + i * 260;
    fr.rect(W / 2 - 400, y - 70, 800, 140, { r: 10, fill: '#FFFFFF', a: a * 0.96 });
    fr.text(t, W / 2, y - 6, {
      font: 'sans', size: 66, color: '#111111', a, align: 'c',
    });
    // 底下配一行小字（第 i 个特性）
    const sub = '0' + (i + 1);
    fr.text(sub, W / 2, y + 44, {
      font: 'mono', size: 22, color: '#888888', a: a * 0.8, align: 'c',
    });
  });
}

/* ---------- 5 局部放大 ---------- */
function card5(fr, lt) {
  const k = ss(lt, 0.1, 1.8);
  const sc = 1 + 0.35 * k;
  const w = 760 * sc, x = (W - w) / 2, y = 560 - (w - 760) * 0.3;
  const a = ss(lt, 0.1, 0.7);
  if (a > 0.003 && IMG.complete && IMG.naturalWidth) {
    const h = w * IMG.naturalHeight / IMG.naturalWidth;
    const ctx = fr.x;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, 4); else ctx.rect(x, y, w, h);
    ctx.clip();
    ctx.drawImage(IMG, x, y, w, h);
    ctx.restore();
  }
  tagBar(fr, '代码全公开', W / 2, 1320, ss(lt, 1.2, 2.0));
}

/* ---------- 6 结论 ---------- */
function card6(fr, lt) {
  const concl = (CT.conclusion || ['完全开源', '拿来就用', '很实用']).slice(0, 3);
  const lines = concl.map(t => String(t).slice(0, 8));
  titleCard(fr, lines, 780, ss(lt, 0.2, 1.3), { size: 76, rot: -0.015 });

  if (REPO) {
    fr.text(REPO, W / 2, 1240, {
      font: 'mono', size: 26, color: '#888888', a: ss(lt, 1.6, 2.3),
    });
  }
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
  const size = Math.min(50, Math.round(860 / (vw * 1.0)));

  fr.text(s.zh, W / 2, 1330, {
    font: 'sans', size, color: '#FFFFFF', a: a * 0.92,
    shadow: 0.7, shadowBlur: 6,
  });
}

const CUES = [
  [T.c1, 'tick'], [T.c2, 'soft'], [T.c3, 'chord', { root: 0 }],
  [T.c4, 'tick'], [T.c5, 'soft'], [T.c6, 'chord', { root: 7 }],
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

VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.42 },
  draw(fr, t) {
    fr.look.bgo = { color: BG };
    fr.look.bloom = 0.03;
    fr.look.grain = 0.03;

    // 网格背景（整片都在，参考视频就是这样）
    fr.look.under = (ctx) => drawGrid(ctx);

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

    fr.text(timecode(t), 40, H - 34, {
      font: 'mono', size: 16, color: '#404040',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'l',
    });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
