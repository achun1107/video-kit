/* 通用影片模板 —— 任何项目都能套
 *
 * 只读 window.CONTENT（content.js），不写死任何项目信息。
 * 内容缺什么就跳过什么，不会报错。
 *
 * 七张卡的固定结构：
 *   1 封面      emoji + 名字 + 一句话 + 三个标签
 *   2 数字墙    stats 里的大数字
 *   3 截图      GitHub 仓库页（放大 + 圈选）
 *   4 特性      features 前 4 条
 *   5 亮点      最大的那个数字
 *   6 清单      chapters / palettes / items（有哪个用哪个）
 *   7 结论      三项总结
 *
 * 配音文案在 audio/copy.json（make-video.mjs 会生成默认版本）
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const EMOJI = CT.emoji || '📦';
const HEAD = CT.headline || (CT.tagline || '一个值得看的开源项目');
const TAG = CT.tagline || '';
const REPO = CT.repo || '';
const VER = CT.version || '';
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const ITEMS = CT.chapters || CT.palettes || CT.items || [];

/* 数字墙取这些键（有就显示） */
const NUM_KEYS = Object.keys(STATS).filter(k => typeof STATS[k] === 'number');

/* ---------- 配色 ---------- */
const C = {
  bg: '#0D0D10',
  card: '#F5EFE3',
  card2: '#FBF7EE',
  ink: '#22252A',
  ink2: '#4A5058',
  mute: '#8A8F98',
  line: '#D9D3C8',
  accent: CT.accent || '#E8613C',
  accent2: CT.accent2 || '#6FE04A',
  gold: '#D4A017',
  white: '#FFFFFF',
};

/* ---------- 时间轴（由 copy.json 的段落数决定，这里是 7 段默认） ---------- */
const DUR = CT.duration || 34.8;
const T = {
  head: 0.15,
  c1: 1.15, c2: 2.20, c3: 8.30, c4: 10.40,
  c5: 13.95, c6: 17.75, c7: 21.15,
  outro: DUR - 3.4,
};

/* ---------- 字幕：从 SRT 转好的 audio/subs.json ---------- */
const SUBS = window.SUBS || [];

/* ---------- 工具 ---------- */
const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60), ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}
function rowA(lt, i, from = 0.1, gap = 0.16) {
  return ss(lt, from + i * gap, from + i * gap + 0.34);
}

function cardBox(fr, k, o = {}) {
  const a = o.a == null ? 1 : o.a;
  if (a <= 0.002) return;
  const x = o.x == null ? 90 : o.x;
  const w = o.w == null ? 900 : o.w;
  const y = o.y == null ? 400 : o.y;
  const h = o.h == null ? 1010 : o.h;
  const r = o.r == null ? 42 : o.r;
  const rise = (1 - k) * 56;
  fr.g({ a }, () => {
    fr.rect(x + 8, y + 26 + rise, w, h, { r, fill: '#000000', a: 0.5 });
    fr.rect(x, y + rise, w, h, { r, fill: C.card });
    fr.rect(x, y + rise, w, h, { r, color: C.accent, w: 2.5, a: 0.92 });
    fr.rect(x + 2, y + rise + 2, w - 4, 120, { r: r - 2, fill: C.card2, a: 0.5 });
  });
}

function header(fr, t, main, sub) {
  const ka = ss(t, T.head, T.head + 0.16);
  if (ka <= 0) return;
  const lines = main.split('\n');
  const size = lines.length > 1 ? 100 : 112;
  lines.forEach((line, i) => {
    const y = 148 + i * (size + 18);
    const ki = ss(t, T.head + i * 0.06, T.head + i * 0.06 + 0.16);
    fr.text(line, W / 2, y + (1 - ki) * 18, {
      font: 'sans', size, color: C.white, a: ki,
      glow: 30, glowColor: '#FFFFFF', glowA: 0.24, shadow: 0.55, shadowBlur: 18,
    });
  });
  const ks = ss(t, T.head + 0.1, T.head + 0.28);
  const subY = 148 + (lines.length - 1) * (size + 18) + size * 0.86;
  fr.text(sub, W / 2, subY + (1 - ks) * 14, {
    font: 'sans', size: 54, color: C.accent2, a: ks,
    glow: 26, glowColor: C.accent2, glowA: 0.5,
  });
}

function seriesBadge(fr, t) {
  const a = ss(t, 0.9, 1.5) * (1 - ss(t, DUR - 0.6, DUR));
  if (a <= 0.004) return;
  const txt = CT.episode || '第 01 期';
  const size = 28;
  const tw = fr.measure(txt, { font: 'sans', size });
  const w = tw + 56, h = 52, x = W - 64 - w, y = 64;
  fr.rect(x, y, w, h, { r: 26, fill: C.accent, a: a * 0.18 });
  fr.rect(x, y, w, h, { r: 26, stroke: C.accent, strokeW: 2, a: a * 0.9 });
  fr.text(txt, x + w / 2, y + h / 2, { font: 'sans', size, color: C.accent, a });
}

function ringMark(fr, cx, cy, rx, ry, k, color, lw) {
  if (k <= 0.004) return;
  const ctx = fr.x;
  const start = -Math.PI * 0.62;
  const sweep = Math.PI * 2.12 * k;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = lw || 5;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, start, start + sweep);
  ctx.stroke();
  ctx.restore();
}

const KEY_RE = /(\d[\d,.]*|[A-Z]{2,}|WCAG AA|MIT)/g;
function richText(fr, str, cy, size, a) {
  const parts = [];
  let last = 0, m;
  KEY_RE.lastIndex = 0;
  while ((m = KEY_RE.exec(str))) {
    if (m.index > last) parts.push([str.slice(last, m.index), false]);
    parts.push([m[0], true]);
    last = m.index + m[0].length;
  }
  if (last < str.length) parts.push([str.slice(last), false]);
  if (!parts.length) parts.push([str, false]);
  const widths = parts.map(([s]) => fr.measure(s, { font: 'sans', size }));
  const total = widths.reduce((x, y) => x + y, 0);
  let x = W / 2 - total / 2;
  parts.forEach(([s, isKey], i) => {
    fr.text(s, x + widths[i] / 2, cy, {
      font: 'sans', size, a,
      color: isKey ? C.accent : C.white,
      shadow: 0.62, shadowBlur: 14, shadowY: 3,
    });
    x += widths[i];
  });
}

function subtitles(fr, t) {
  if (!SUBS.length) return;
  const cand = SUBS.filter(x => t >= x.a - 0.05 && t <= x.b + 0.25);
  const s = cand.length ? cand[cand.length - 1] : null;
  if (!s) return;
  const a = ss(t, s.a, s.a + 0.18) * (1 - ss(t, s.b, s.b + 0.1));
  if (a <= 0.003) return;
  const vw = Array.from(s.zh).reduce((n, ch) => n + (/[\u4e00-\u9fff]/.test(ch) ? 1 : (ch === ' ' ? 0.3 : 0.56)), 0);
  const size = Math.min(140, Math.round(880 / (vw * 0.96)));
  richText(fr, s.zh, 1508, size, a);
}

/* ---------- 素材 ---------- */
const REPO_IMG = new Image();
REPO_IMG.src = 'assets/repo.png';
window.__IMAGES = [REPO_IMG];
const REPO_STAR = (CT.stats && CT.stats.star) || 0;
const REPO_FORK = (CT.stats && CT.stats.fork) || 0;

function shot(fr, img, x, y, w, o) {
  if (!img || !img.complete || !img.naturalWidth) {
    fr.rect(x, y, w, w * 0.6, { r: 14, fill: '#1A1D22' });
    return 0;
  }
  const h = w * img.naturalHeight / img.naturalWidth;
  const ctx = fr.x;
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, (o && o.r) || 14); else ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
  return h;
}

/* ---------- 1 封面 ---------- */
function card1(fr, lt) {
  const k = ss(lt, 0, 0.75);
  cardBox(fr, k);
  fr.text(EMOJI, W / 2, 640, { font: 'sans', size: 150, a: rowA(lt, 0, 0.15) * 0.95 });
  fr.text(NAME, W / 2, 830, { font: 'sans', size: 104, color: C.ink, a: rowA(lt, 1, 0.2) });
  fr.text(HEAD.slice(0, 14), W / 2, 950, { font: 'sans', size: 52, color: C.ink2, a: rowA(lt, 2, 0.3) });
  if (TAG) fr.text(TAG.slice(0, 22), W / 2, 1030, { font: 'sans', size: 34, color: C.mute, a: rowA(lt, 3, 0.4) });

  const tags = [];
  if (STATS.palettes) tags.push(`${STATS.palettes} 套配色`);
  if (STATS.chapters) tags.push(`${STATS.chapters} 章`);
  if (STATS.features) tags.push(`${STATS.features} 项特性`);
  if (STATS.deps === 0) tags.push('0 依赖');
  if (STATS.license) tags.push(STATS.license);
  const use = tags.slice(0, 3);
  if (use.length) {
    const tw = 240, gap = 24, total = tw * use.length + gap * (use.length - 1);
    use.forEach((s, i) => {
      const a = rowA(lt, 4, 0.55, 0.14);
      const x0 = (W - total) / 2 + i * (tw + gap);
      fr.rect(x0, 1120, tw, 84, { r: 42, fill: C.accent, a: a * 0.16 });
      fr.rect(x0, 1120, tw, 84, { r: 42, stroke: C.accent, strokeW: 2, a: a * 0.6 });
      fr.text(s, x0 + tw / 2, 1162, { font: 'sans', size: 30, color: C.ink, a });
    });
  }
  if (VER) fr.text(`v${VER}`, W / 2, 1300, { font: 'mono', size: 28, color: C.mute, a: rowA(lt, 5, 0.75) });
}

/* ---------- 2 数字墙 ---------- */
function card2(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  fr.text('几个数字', W / 2, 500, { font: 'sans', size: 46, color: C.ink, a: rowA(lt, 0) });

  const nums = NUM_KEYS.slice(0, 4);
  if (!nums.length) {
    fr.text('全部开源', W / 2, 760, { font: 'sans', size: 84, color: C.accent, a: rowA(lt, 1) });
    return;
  }
  const cols = nums.length <= 2 ? nums.length : 2;
  const rows = Math.ceil(nums.length / cols);
  const cw = 320, ch = 220;
  const x0 = (W - cols * cw) / 2 + cw / 2;
  const y0 = 720;

  nums.forEach((key, i) => {
    const c = i % cols, r = Math.floor(i / cols);
    const a = rowA(lt, 1 + i, 0.2, 0.14);
    if (a <= 0.003) return;
    const cx = x0 + c * cw, cy = y0 + r * ch;
    fr.text(String(STATS[key]), cx, cy, {
      font: 'sans', size: 132, color: i === 0 ? C.accent : C.ink, a,
      glow: i === 0 ? 28 : 0, glowColor: C.accent, glowA: 0.28, align: 'c',
    });
    const label = CT.statLabels && CT.statLabels[key] ? CT.statLabels[key] : key;
    fr.text(label, cx, cy + 88, { font: 'sans', size: 26, color: C.mute, a, align: 'c' });
  });
}

/* ---------- 3 截图 ---------- */
function card3(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  fr.text('就放在 GitHub 上', W / 2, 480, { font: 'sans', size: 44, color: C.ink, a: rowA(lt, 0) });
  fr.text('全部开源，随时能翻', W / 2, 536, { font: 'sans', size: 27, color: C.mute, a: rowA(lt, 1, 0.12) });

  const a0 = rowA(lt, 2, 0.15);
  if (a0 > 0.003) {
    const w = 700;
    const ratio = (REPO_IMG.naturalWidth && REPO_IMG.naturalHeight)
      ? REPO_IMG.naturalHeight / REPO_IMG.naturalWidth : 0.86;
    const h = Math.round(w * ratio);
    const x = (W - w) / 2, y = 620;
    fr.rect(x - 4, y - 4, w + 8, h + 8, { r: 18, fill: '#0F0F12', a: a0 });
    fr.g({ a: a0 }, () => shot(fr, REPO_IMG, x, y, w, { r: 14 }));
    const rk = ss(lt, 0.9, 1.7);
    if (rk > 0.004) ringMark(fr, x + w / 2, y + h / 2, w * 0.28, 28, rk, C.accent, 5);
  }

  if (REPO_STAR || REPO_FORK) {
    const aS = rowA(lt, 3, 0.5);
    const yN = 1170;
    fr.text(String(REPO_STAR), W / 2 - 150, yN, { font: 'sans', size: 88, color: C.accent, a: aS, align: 'c' });
    fr.text('Star', W / 2 - 150, yN + 62, { font: 'sans', size: 26, color: C.mute, a: aS, align: 'c' });
    fr.text(String(REPO_FORK), W / 2 + 150, yN, { font: 'sans', size: 88, color: C.ink, a: aS, align: 'c' });
    fr.text('Fork', W / 2 + 150, yN + 62, { font: 'sans', size: 26, color: C.mute, a: aS, align: 'c' });
  }
}

/* ---------- 4 特性 ---------- */
function card4(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  fr.text('它能干什么', W / 2, 490, { font: 'sans', size: 46, color: C.ink, a: rowA(lt, 0) });

  const list = FEATURES.slice(0, 4);
  if (!list.length) {
    fr.text('看 README 更全', W / 2, 760, { font: 'sans', size: 40, color: C.mute, a: rowA(lt, 1) });
    return;
  }
  list.forEach((f, i) => {
    const a = rowA(lt, 1 + i, 0.2, 0.18);
    if (a <= 0.003) return;
    const y = 640 + i * 160;
    const title = (typeof f === 'string') ? f : (f.title || f.name || '');
    const desc = (typeof f === 'string') ? '' : (f.desc || f.hint || '');
    fr.rect(150, y - 56, 780, 128, { r: 22, fill: '#EFE7D8', a: a * 0.7 });
    fr.text(String(i + 1).padStart(2, '0'), 200, y, { font: 'mono', size: 30, color: C.accent, a, align: 'l' });
    fr.text(title.slice(0, 16), 270, desc ? y - 16 : y, { font: 'sans', size: 32, color: C.ink, a, align: 'l' });
    if (desc) fr.text(desc.slice(0, 22), 270, y + 26, { font: 'sans', size: 22, color: C.mute, a, align: 'l' });
  });
}

/* ---------- 5 亮点 ---------- */
function card5(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  const big = NUM_KEYS.length ? STATS[NUM_KEYS[0]] : null;
  fr.text('一句话记住它', W / 2, 490, { font: 'sans', size: 42, color: C.ink, a: rowA(lt, 0) });

  if (big != null) {
    const ka = ss(lt, 0.25, 0.85);
    fr.text(String(big), W / 2, 780, {
      font: 'sans', size: 300, color: C.accent, a: ka, glow: 36, glowColor: C.accent, glowA: 0.32,
    });
    const label = CT.statLabels && CT.statLabels[NUM_KEYS[0]] ? CT.statLabels[NUM_KEYS[0]] : NUM_KEYS[0];
    fr.text(label, W / 2, 940, { font: 'sans', size: 44, color: C.ink, a: rowA(lt, 2, 0.5) });
  } else {
    fr.text(EMOJI, W / 2, 800, { font: 'sans', size: 200, a: ss(lt, 0.25, 0.85) });
  }

  const a2 = rowA(lt, 3, 0.7);
  fr.text(TAG.slice(0, 20) || '零依赖 · 开源', W / 2, 1080, { font: 'sans', size: 32, color: C.ink2, a: a2 });
}

/* ---------- 6 清单 ---------- */
function card6(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  const title = CT.listTitle || '都有什么';
  fr.text(title, W / 2, 480, { font: 'sans', size: 44, color: C.ink, a: rowA(lt, 0) });

  const list = ITEMS.slice(0, 12);
  if (!list.length) {
    fr.text('详见仓库', W / 2, 760, { font: 'sans', size: 40, color: C.mute, a: rowA(lt, 1) });
    return;
  }
  const cols = list.length > 6 ? 2 : 1;
  const perCol = Math.ceil(list.length / cols);
  const x0 = cols === 2 ? 180 : 260;
  const colw = 400;
  list.forEach((it, i) => {
    const col = Math.floor(i / perCol), row = i % perCol;
    const a = rowA(lt, 1 + i, 0.18, 0.07);
    if (a <= 0.003) return;
    const x = x0 + col * colw, y = 620 + row * 66;
    const name = (typeof it === 'string') ? it : (it.title || it.name || it.no || '');
    const no = (typeof it === 'object' && it.no) ? it.no : String(i + 1).padStart(2, '0');
    fr.rect(x - 14, y - 24, 40, 40, { r: 10, fill: C.accent, a: a * 0.16 });
    fr.rect(x - 14, y - 24, 40, 40, { r: 10, stroke: C.accent, strokeW: 2, a: a * 0.5 });
    fr.text(no, x + 6, y - 4, { font: 'mono', size: 20, color: C.ink, a });
    fr.text(String(name).slice(0, 12), x + 46, y - 3, { font: 'sans', size: 26, color: C.ink2, a, align: 'l' });
  });
}

/* ---------- 7 结论 ---------- */
function card7(fr, lt) {
  const k = ss(lt, 0, 0.7);
  cardBox(fr, k);
  const concl = (CT.conclusion && CT.conclusion.length ? CT.conclusion : ['完全免费', '完全开源', '三分钟上手']).slice(0, 3);
  const colors = [C.accent, C.ink, C.ink];
  concl.forEach((s, i) => {
    const a = rowA(lt, i, 0.1, 0.26);
    const y = 620 + i * 116;
    const dx = (1 - a) * 36;
    fr.text(s, W / 2 - dx, y, {
      font: 'sans', size: 90, color: colors[i], a,
      glow: i === 0 ? 24 : 0, glowColor: C.accent, glowA: 0.24,
    });
  });
  const a2 = rowA(lt, 3, 1.0);
  fr.line(300, 1060, 780, 1060, { w: 2, color: C.line, a: a2 });
  if (REPO) fr.text(REPO, W / 2, 1125, { font: 'mono', size: 32, color: C.ink2, a: a2 });
  fr.text(`v${VER || '1.0'} · 开源`, W / 2, 1195, { font: 'sans', size: 27, color: C.mute, a: rowA(lt, 4, 1.2) });
}

/* ---------- 音效 ---------- */
const CUES = [
  [T.c1, 'chord', { root: 0 }], [T.c2, 'chord', { root: 5 }],
  [T.c3, 'chord', { root: 3 }], [T.c4, 'chord', { root: 7 }],
  [T.c5, 'chord', { root: 5 }], [T.c6, 'chord', { root: 0 }],
  [T.c7, 'chord', { root: 7 }],
  [0.15, 'tick'], [0.44, 'tick'], [0.72, 'tick'],
  [2.60, 'bloom', { root: 0 }], [13.95, 'bloom', { root: 7 }], [21.10, 'rise'],
  [21.60, 'thud'], [23.00, 'thud'], [24.50, 'thud'],
  [DUR - 1.4, 'hush'],
];

/* ---------- 主绘制 ---------- */
VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.55 },
  draw(fr, t) {
    fr.look.bgo = { color: C.bg };
    fr.look.bloom = 0.12;
    fr.look.grain = 0.05;
    fr.look.under = (ctx, tt) => {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 120; i++) {
        const px = hash(i * 1.7 + 3) * W, py = hash(i * 2.3 + 11) * H;
        const s = hash(i + 41), r = s > 0.93 ? 2.0 : s > 0.62 ? 1.3 : 0.9;
        const a = (0.04 + 0.16 * s * s) * (0.7 + 0.3 * Math.sin(tt * (0.5 + s * 1.2) + i));
        ctx.fillStyle = `rgba(${s > 0.8 ? '215,225,245' : '150,160,180'},${a})`;
        ctx.beginPath(); ctx.arc(px, py, r, 0, 6.2832); ctx.fill();
      }
      const g = ctx.createRadialGradient(W / 2, 120, 0, W / 2, 120, W * 0.9);
      g.addColorStop(0, 'rgba(40,48,66,0.55)'); g.addColorStop(1, 'rgba(40,48,66,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, 700);
      ctx.restore();
    };

    header(fr, t, CT.headerMain || '一个开源项目\n值得看看', CT.headerSub || '');
    seriesBadge(fr, t);

    const segs = [
      [T.c1, T.c2, card1], [T.c2, T.c3, card2], [T.c3, T.c4, card3],
      [T.c4, T.c5, card4], [T.c5, T.c6, card5], [T.c6, T.c7, card6],
      [T.c7, DUR, card7],
    ];
    segs.forEach(([a, b, fn]) => {
      if (t < a || t >= b) return;
      const kk = Math.min(seg(t, a, a + 0.06), 1 - seg(t, b - 0.05, b));
      if (kk <= 0.002) return;
      fr.g({ a: kk }, () => fn(fr, t - a));
    });

    subtitles(fr, t);

    for (const s of SUBS) if (Math.abs(t - s.a) < 0.02) fr.sfx(s.a, 'tick');

    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    const ta = ss(t, 0.5, 1.2) * 0.85;
    fr.text(timecode(t), 74, H - 74, { font: 'mono', size: 22, color: '#6A6A75', a: ta, align: 'l' });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.04, '#000000');
  },
});
