/* 风格 A：录屏讲解（参考 ajin / 阿津AI库）
 *
 * 特征：真实界面截图铺满屏（原色不压暗）+ 黄色荧光笔高亮 + 黄色手写感大字叠加。
 * 节奏：一句话配一段截图，截图先出、字后压上来。
 *
 * 和 tech 模板的区别：没有白卡片，没有边框，就是截图 + 字。
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const REPO = CT.repo || '';

const DUR = 34.8;

/* 参考视频的配色：黄色荧光笔 + 黄色手写体 + 深色底 */
const BG = '#0A0A0A';
const YELLOW = '#FFE500';
const HILITE = 'rgba(255,229,0,0.38)';   // 荧光笔（半透明黄）

const T = {
  c1: 0, c2: 6.5, c3: 12.5, c4: 18.5, c5: 24.5, c6: 30.0,
  outro: DUR - 2.0,
};

const SUBS = window.SUBS || [];

/* 本套的关注引导话术 */
const CTA_TEXT = '关注我，手把手带你玩开源';

/* 手写字体：运行时挂到 VK.FONTS 上，不改引擎。
 * MaShanZheng（马善政楷书）是 SIL OFL，笔画有粗细变化，最接近参考视频的手写感。 */
if (VK.FONTS) VK.FONTS.hand = ['400', '"VK Hand", "VK Sans"'];


const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

/* 黄色手写感大字：粗黑体 + 黑色描边 + 微微倾斜，视觉上接近手写 */
function marker(fr, text, x, y, size, a, o) {
  o = o || {};
  if (a <= 0.003) return;
  const rot = o.rot == null ? -0.035 : o.rot;
  const ctx = fr.x;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  // 描边（黑），让黄字在亮截图上也看得清
  fr.text(text, 0, 0, {
    font: 'hand', size, color: '#000000',
    a: a * 0.5, align: o.align || 'c',
    shadow: 0,
  });
  fr.text(text, 0, 0, {
    font: 'hand', size, color: o.color || YELLOW, a, align: o.align || 'c',
  });
  ctx.restore();
}

/* 荧光笔：在文字底下刷一道半透明的黄色横条 */
function highlighter(fr, x, y, w, h, k, a) {
  if (k <= 0.003) return;
  const ww = w * Math.min(1, k);
  fr.rect(x - ww / 2, y - h / 2, ww, h, { fill: YELLOW, a: (a || 1) * 0.30 });
}

/* 截图：铺满屏，轻微推拉 */
function shotFull(fr, img, k) {
  if (!img || !img.complete || !img.naturalWidth) {
    fr.rect(0, 0, W, H, { fill: '#141414' });
    return;
  }
  const ctx = fr.x;
  // contain：完整显示（cover 会裁掉左右，项目名和 star 就没了）
  const sc = 1.0 + 0.04 * k;
  const w = W * 0.96 * sc;
  const h = w * img.naturalHeight / img.naturalWidth;
  const dx = (W - w) / 2;
  const dy = 120 + (1400 - h) / 2;
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, W, 1400);
  ctx.clip();
  ctx.drawImage(img, dx, dy, w, h);
  ctx.restore();
}

const IMG = new Image();
IMG.src = 'assets/repo.png';
window.__IMAGES = [IMG];

/* ---------- 1 开场：项目名 + star ---------- */
function card1(fr, lt) {
  // 硬切：第 0 帧就满，不淡入（抖音前 1 秒空屏等于放弃观众）
  const k = 1;
  shotFull(fr, IMG, ss(lt, 0, 2.2));

  // 压一层深色，让字出来
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.42 * k });

  marker(fr, NAME, W / 2, 700, 120, 1, { rot: -0.05 });

  const star = STATS.star;
  if (star) {
    const a2 = 1;   // star 第 0 帧就出，不等 0.8 秒
    highlighter(fr, W / 2, 880, 620, 90, ss(lt, 0.9, 2.0), a2);
    marker(fr, `GitHub 上 ${star.toLocaleString('en-US')} star`,
           W / 2, 880, 56, a2, { rot: -0.02 });
  }
}

/* ---------- 2 卖点 ---------- */
function card2(fr, lt) {
  const k = ss(lt, 0.1, 1.4);
  shotFull(fr, IMG, 0.5 + ss(lt, 0, 3.0) * 0.5);
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.48 * k });

  const line = HEAD || '一个值得看看的开源项目';
  const chars = Array.from(line);
  const rows = [];
  for (let i = 0; i < chars.length; i += 8) rows.push(chars.slice(i, i + 8).join(''));

  rows.forEach((r, i) => {
    const a = i === 0 ? 1 : ss(lt, 0.2 + i * 0.45, 0.2 + i * 0.45 + 0.9);
    if (a <= 0.003) return;
    // 字号随行长自适应：手写体字距大，11 字 × 78px 就超 1080 了
    const fs = r.length >= 8 ? 56 : (r.length >= 6 ? 64 : 72);
    const y = 700 + i * 150;
    highlighter(fr, W / 2, y, 900, fs * 1.35, ss(lt, 0.2 + i * 0.5, 0.2 + i * 0.5 + 1.2), a);
    marker(fr, r, W / 2, y, fs, a, { rot: i % 2 ? 0.02 : -0.025 });
  });
}

/* ---------- 3 三个特性 ---------- */
function card3(fr, lt) {
  const k = ss(lt, 0.1, 1.2);
  shotFull(fr, IMG, 0.8);
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.52 * k });

  const list = FEATURES.slice(0, 3).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')).slice(0, 14));
  const rows = list.length ? list : ['开箱即用', '零依赖', '完全开源'];

  rows.forEach((t, i) => {
    const a = i === 0 ? 1 : ss(lt, 0.35 + i * 0.75, 0.35 + i * 0.75 + 1.0);
    if (a <= 0.003) return;
    const y = 620 + i * 200;
    // 字号随字数自适应：手写体字距大，12 字 × 92px = 1104px 会超出 1080
    const n = Array.from(t).length;
    const fs = n <= 8 ? 82 : (n <= 10 ? 70 : (n <= 12 ? 60 : 52));
    marker(fr, t, W / 2, y, fs, a, { rot: i % 2 ? 0.03 : -0.04 });
  });
}

/* ---------- 4 大数字 ---------- */
function card4(fr, lt) {
  shotFull(fr, IMG, 1.2);
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.55 });

  const star = STATS.star || 0;
  if (!star) {
    marker(fr, '完全开源', W / 2, 800, 120, ss(lt, 0.2, 1.4));
    return;
  }

  const k = ss(lt, 0, 0.8);   // 快滚 + 硬切，别让切进来时是空的
  const shown = Math.round(star * E.out3(k));
  fr.text(shown.toLocaleString('en-US'), W / 2, 780, {
    font: 'sans', size: 220, color: YELLOW, a: 1,
  });
  marker(fr, 'STAR', W / 2, 940, 66, ss(lt, 1.0, 1.7), { rot: 0 });
}

/* ---------- 5 截图细节 ---------- */
function card5(fr, lt) {
  const k = ss(lt, 0.1, 1.3);
  shotFull(fr, IMG, 1.6);
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.25 * k });

  const a = ss(lt, 1.2, 2.2);
  highlighter(fr, W / 2, 1180, 720, 100, ss(lt, 1.1, 2.2), a);
  marker(fr, '就是这个界面', W / 2, 1180, 62, a);
}

/* ---------- 6 结论 ---------- */
function card6(fr, lt) {
  shotFull(fr, IMG, 2.0);
  fr.rect(0, 0, W, H, { fill: '#000000', a: 0.58 });

  const concl = (CT.conclusion || ['完全开源', '拿来就用', '三分钟上手']).slice(0, 3);
  concl.forEach((t, i) => {
    const a = i === 0 ? 1 : ss(lt, 0.25 + i * 0.65, 0.25 + i * 0.65 + 0.95);
    if (a <= 0.003) return;
    marker(fr, String(t).slice(0, 12), W / 2, 660 + i * 190, 96, a,
           { rot: i % 2 ? 0.025 : -0.03 });
  });

  if (REPO) {
    fr.text(REPO, W / 2, 1320, {
      font: 'mono', size: 26, color: '#888888', a: ss(lt, 2.2, 2.9),
    });
  }

  // 结尾引导（系列号 + 关注）
  outroBar(fr, 1, { y: 1290 });
}

/* ---------- 字幕 ---------- */
function subtitles(fr, t) {
  if (!SUBS.length) return;
  const cand = SUBS.filter(x => t >= x.a - 0.05 && t <= x.b + 0.25);
  const s = cand.length ? cand[cand.length - 1] : null;
  if (!s) return;
  const a = ss(t, s.a, s.a + 0.16) * (1 - ss(t, s.b, s.b + 0.1));
  if (a <= 0.003) return;

  const vw = Array.from(s.zh).reduce(
    (n, ch) => n + (/[\u4e00-\u9fff]/.test(ch) ? 1 : (ch === ' ' ? 0.3 : 0.56)), 0);
  const size = Math.min(54, Math.round(860 / (vw * 1.0)));

  fr.rect(W / 2 - 480, 1330 - size * 0.9, 960, size * 1.8, {
    fill: '#000000', a: a * 0.6,
  });
  fr.text(s.zh, W / 2, 1330, {
    font: 'sans', size, color: '#FFFFFF', a,
    shadow: 0.95, shadowBlur: 10,
  });
}

const CUES = [
  [T.c1, 'rise'], [T.c2, 'tick'], [T.c3, 'tick'],
  [T.c4, 'chord', { root: 0 }], [T.c5, 'soft'], [T.c6, 'chord', { root: 7 }],
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
  fr.rect(0, y - 56, W, 210, { fill: '#000000', a: a * 0.82 });

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


/* 鼠标光标：白色箭头 + 点击涟漪。
 *
 * 参考视频里都有这个 —— 观众看到光标动，才知道"这是真在操作"，
 * 不是"PPT 放了一张图"。
 *
 * 路径用固定的控制点，t 的纯函数，--det 能过。
 */
function cursor(fr, t, t0, dur, x0, y0, x1, y1, clickAt) {
  if (t < t0 || t > t0 + dur + 0.6) return;

  const k = Math.min(1, Math.max(0, (t - t0) / dur));
  const e = E.io3(k);
  // 带一点弧线：控制点在两点中间上方
  const cx = (x0 + x1) / 2 + (y1 - y0) * 0.18;
  const cy = (y0 + y1) / 2 - Math.abs(x1 - x0) * 0.12;
  // 二次贝塞尔
  const x = (1 - e) * (1 - e) * x0 + 2 * (1 - e) * e * cx + e * e * x1;
  const y = (1 - e) * (1 - e) * y0 + 2 * (1 - e) * e * cy + e * e * y1;

  const ctx = fr.x;
  const a = t < t0 + 0.12 ? (t - t0) / 0.12 : 1;

  // 点击涟漪
  if (clickAt != null && t >= t0 + clickAt) {
    const ck = Math.min(1, (t - t0 - clickAt) / 0.45);
    if (ck < 1) {
      const r = 14 + 46 * ck;
      ctx.save();
      ctx.strokeStyle = `rgba(255,229,0,${0.75 * (1 - ck)})`;
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
  }

  // 光标本体：白色箭头 + 黑描边
  ctx.save();
  ctx.globalAlpha = a * 0.96;
  ctx.translate(x, y);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, 30);
  ctx.lineTo(8, 23);
  ctx.lineTo(13, 34);
  ctx.lineTo(18, 31);
  ctx.lineTo(13, 21);
  ctx.lineTo(23, 21);
  ctx.closePath();
  ctx.fillStyle = '#FFFFFF';
  ctx.fill();
  ctx.strokeStyle = '#000000';
  ctx.lineWidth = 2.2;
  ctx.lineJoin = 'round';
  ctx.stroke();
  ctx.restore();
}

VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.45 },
  draw(fr, t) {
    fr.look.bgo = { color: BG };
    fr.look.bloom = 0.05;
    fr.look.grain = 0.045;

    const segs = [
      [T.c1, T.c2, card1], [T.c2, T.c3, card2], [T.c3, T.c4, card3],
      [T.c4, T.c5, card4], [T.c5, T.c6, card5], [T.c6, DUR, card6],
    ];

    segs.forEach(sg => cut(fr, t, sg[0], sg[1], sg[2]));

    /* 鼠标光标：让静态截图有被操作的观感 */
    cursor(fr, t, 0.9, 1.1, W * 0.84, H * 0.55, W * 0.845, H * 0.28, 0.8);
    cursor(fr, t, 13.5, 1.3, W * 0.22, H * 0.60, W * 0.60, H * 0.34, 1.0);

    subtitles(fr, t);

    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    fr.text(timecode(t), 40, H - 34, {
      font: 'mono', size: 16, color: '#444444',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'l',
    });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
