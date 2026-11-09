/* 风格 B：手账批注（参考 ganhuoju / 开源工具干货局）
 *
 * 特征：截图整体压暗（半透明黑遮罩）+ 超大黄色手写感文字压在脸上。
 * 和 ajin 的区别：ajin 的截图是原色、字是配角；ganhuoju 的字是主角，截图只是背景板。
 *
 * 节奏：句子一句一句压上来，每句停留 3-4 秒，像在别人截图上做批注。
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const REPO = CT.repo || '';

const DUR = 34.8;

const BG = '#050505';
const YELLOW = '#F5E400';

const T = {
  cover: 0.5,     // 设计封面
  c1: 3.6, c2: 8.4, c3: 13.2, c4: 18.0, c5: 23.0, c6: 28.0,
  outro: DUR - 2.0,
};

const SUBS = window.SUBS || [];

/* 本套的关注引导话术 */
const CTA_TEXT = '关注我，每天一个值得抄的项目';

/* 手写字体：运行时挂到 VK.FONTS 上，不改引擎。
 * MaShanZheng（马善政楷书）是 SIL OFL，笔画有粗细变化，最接近参考视频的手写感。 */
if (VK.FONTS) VK.FONTS.hand = ['400', '"VK Hand", "VK Sans"'];


const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

/* 超大黄色手写感：逐字随机倾斜 + 黑描边，模仿真人马克笔批注
 *
 * 为什么要逐字：整行一起旋转看起来像"排版歪了"，不像手写。
 * 真人写字每个字角度都差一点。角度用 hash(i) 取，保证 --det 通过。
 */
function scrawl(fr, text, x, y, size, a, o) {
  o = o || {};
  if (a <= 0.003) return;

  const chars = Array.from(text);
  if (!chars.length) return;

  const off = Math.max(1.2, size * 0.020);   // 手写体笔画细，描边收窄
  const dirs = [[-off, 0], [off, 0], [0, -off], [0, off]];
  const ctx = fr.x;

  // 先量每个字的宽度，算总宽和起始位置
  const widths = chars.map(ch => fr.measure(ch, { font: 'hand', size }));
  const total = widths.reduce((p, c) => p + c, 0);
  const align = o.align || 'c';
  let cx = align === 'l' ? x : (align === 'r' ? x - total : x - total / 2);

  const baseRot = o.rot == null ? -0.03 : o.rot;

  chars.forEach((ch, i) => {
    const w = widths[i];
    const mx = cx + w / 2;

    // 逐字角度：基础倾斜 + 每字 ±2.5° 的随机偏移
    const jitter = (hash(i * 7.3 + 2.1) - 0.5) * 0.09;
    const rot = baseRot + jitter;

    // 逐字垂直微抖（真人写字基线也会飘）
    const dy = (hash(i * 3.7 + 9.4) - 0.5) * size * 0.045;

    ctx.save();
    ctx.translate(mx, y + dy);
    ctx.rotate(rot);

    // 描边
    for (const [dx, dyy] of dirs) {
      fr.text(ch, dx, dyy, {
        font: 'hand', size, color: '#000000', a: a * 0.95, align: 'c',
      });
    }
    // 主体
    fr.text(ch, 0, 0, {
      font: 'hand', size, color: o.color || YELLOW, a, align: 'c',
    });
    ctx.restore();

    cx += w;
  });
}

/* 截图铺底，统一压暗 */
function bed(fr, img, dark, z) {
  // z: 缩放系数（Ken Burns）。传 1.0~1.06 让静止截图一直在缓慢放大，
  // 不然每张卡 4.4 秒里画面完全不动，看起来像 PPT 播放。
  const zoom = z || 1;
  if (img && img.complete && img.naturalWidth) {
    // contain：完整显示截图（cover 会裁掉左右两边，项目名和 star 就没了）
    const ctx = fr.x;
    const w = W * 0.94 * zoom;
    const h = w * img.naturalHeight / img.naturalWidth;
    const x = (W - w) / 2, y = (H - h) / 2;
    // 先铺一层深色渐变底，把上下空出来的地方填掉
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#0D1117');
    g.addColorStop(0.5, '#161B22');
    g.addColorStop(1, '#0D1117');
    ctx.save();
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
    // 再贴完整截图，加一圈细边
    fr.rect(x - 3, y - 3, w + 6, h + 6, { fill: '#30363D', a: 0.9 });
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, W, H);
    ctx.clip();
    ctx.drawImage(img, x, y, w, h);
    ctx.restore();
  } else {
    fr.rect(0, 0, W, H, { fill: '#0E0E0E' });
  }
  fr.rect(0, 0, W, H, { fill: '#000000', a: dark == null ? 0.62 : dark });
}

const IMG = new Image();
IMG.src = 'assets/repo.png';
window.__IMAGES = [IMG];

/* ---------- 0 设计封面（参考视频第一帧的思路：Logo + 项目名 + 三个标签）---------- */
function cover(fr, lt) {
  fr.rect(0, 0, W, H, { fill: '#0A1015', a: 1 });

  // 入场动画：第 0 帧就有「133」，其余元素 1 秒内依次出现。
  // 原来全部 a:1 硬切，前 3.6 秒画面完全静止 —— 抖音上等于劝人划走。
  const t01 = (a, b) => Math.max(0, Math.min(1, (lt - a) / (b - a)));
  const ease = x => 1 - Math.pow(1 - x, 3);   // easeOutCubic

  // ── star 大数字（最强钩子，第 0 帧就出，但带一个放大）──
  const star = STATS.star;
  if (star) {
    // 起始 alpha 0.78：第 0 帧「133」就清晰可见，
    // 但仍有放大+变亮的动感。
    // （之前写 0.35 起始，preflight 报首帧太暗：亮点占比 0.8%）
    const p1 = ease(t01(0, 0.45));
    fr.text(star.toLocaleString('en-US'), W / 2, 200, {
      font: 'sans', size: 130 * (0.94 + 0.06 * p1), color: YELLOW,
      a: 0.85 + 0.15 * p1, align: 'c',
    });
    const p2 = ease(t01(0.15, 0.55));
    fr.text('GitHub 星标', W / 2, 320, {
      font: 'sans', size: 40, color: '#8FA3B0', a: p2, align: 'c',
    });
  }

  // ── 项目名：从下方滑入 ──
  const p3 = ease(t01(0.25, 0.75));
  fr.text(NAME, W / 2, 440 + 40 * (1 - p3), {
    font: 'sans', size: 96, color: '#FFFFFF', a: p3, align: 'c',
  });

  // ── 一句话 ──
  const p4 = ease(t01(0.5, 1.0));
  if (HEAD) {
    fr.text(HEAD, W / 2, 540 + 24 * (1 - p4), {
      font: 'sans', size: 44, color: '#8FA3B0', a: p4, align: 'c',
    });
  }

  // ── 截图：先放大入场，之后持续缓慢放大 ──
  const p5 = ease(t01(0.0, 0.9));
  if (IMG.complete && IMG.naturalWidth) {
    const kb = 1 + 0.035 * Math.max(0, lt - 0.9) / 2.7;   // 0.9s 之后继续推
    const sc = (0.94 + 0.06 * p5) * kb;
    const w = 760, h = w * IMG.naturalHeight / IMG.naturalWidth;
    const cx = W / 2, cy = 620 + h / 2;
    const ctx = fr.x;
    ctx.save();
    // 起始 0.55：第 0 帧截图已经可见（撑起亮度检查），但仍有淡入
    ctx.globalAlpha = 0.55 + 0.45 * p5;
    ctx.translate(cx, cy);
    ctx.scale(sc, sc);
    ctx.translate(-cx, -cy);
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect((W - w) / 2, 620, w, h, 20);
    else ctx.rect((W - w) / 2, 620, w, h);
    ctx.clip();
    ctx.drawImage(IMG, (W - w) / 2, 620, w, h);
    ctx.restore();
  }
}

/* ---------- 1 大字点名 ---------- */
function card1(fr, lt) {
  bed(fr, IMG, 0.66, 1 + 0.06 * Math.min(1, lt / 4.4));
  scrawl(fr, NAME, W / 2, 760, 150, 1, { rot: -0.06 });   // 硬切，名字第 0 帧就出
  scrawl(fr, '来了', W / 2 + 60, 940, 96, ss(lt, 0.55, 1.4), { rot: 0.05 });   // 提前出现，别让画面空着
}

/* ---------- 2 star ---------- */
function card2(fr, lt) {
  bed(fr, IMG, 0.6, 1 + 0.06 * Math.min(1, lt / 4.4));
  const star = STATS.star;
  if (star) {
    // 硬切 + 数字快滚：原来 0.2~1.6 秒淡入，切进来时几乎是空的
    const k = ss(lt, 0, 0.7);
    const shown = Math.round(star * E.out3(k));
    scrawl(fr, `狂揽 ${shown.toLocaleString('en-US')} star`,
           W / 2, 760, 92, 1, { rot: -0.035 });
  } else {
    scrawl(fr, '完全开源', W / 2, 760, 120, ss(lt, 0.2, 1.4));
  }
}

/* ---------- 3 最厉害的地方 ---------- */
function card3(fr, lt) {
  bed(fr, IMG, 0.64, 1 + 0.06 * Math.min(1, lt / 4.4));
  scrawl(fr, '它到底能干什么', W / 2, 720, 84, 1, { rot: -0.03 });
  if (HEAD) {
    // 按字数分行 + 字号随行长自适应（原来 slice(0,12) 会把「搞定一切」切掉）
    const chars = Array.from(HEAD);
    const per = Math.min(11, Math.ceil(chars.length / 2));
    const rows = [];
    for (let i = 0; i < chars.length; i += per) {
      rows.push(chars.slice(i, i + per).join(''));
    }
    rows.slice(0, 2).forEach((r, i) => {
      const size = r.length >= 10 ? 72 : (r.length >= 8 ? 82 : 92);
      scrawl(fr, r, W / 2, 880 + i * 112, size,
             ss(lt, 0.5 + i * 0.3, 1.4 + i * 0.3), { rot: 0.04 });
    });
  }
}

/* ---------- 4 场景：不管怎么变 ---------- */
function card4(fr, lt) {
  bed(fr, IMG, 0.66, 1 + 0.06 * Math.min(1, lt / 4.4));
  // 从 features[1] 读，不再写死「不管怎么变都能自动适配」
  const f = FEATURES[1];
  const t = String((typeof f === 'string') ? f : (f && (f.title || f.name)) || '');
  scrawl(fr, '第二个亮点', W / 2, 700, 84, 1, { rot: -0.05 });
  if (t) {
    const chars = Array.from(t);
    const per = Math.min(11, Math.ceil(chars.length / 2));
    const rows = [];
    for (let i = 0; i < chars.length; i += per) {
      rows.push(chars.slice(i, i + per).join(''));
    }
    rows.slice(0, 2).forEach((r, i) => {
      const size = r.length >= 10 ? 72 : 86;
      scrawl(fr, r, W / 2, 880 + i * 110, size,
             ss(lt, 0.5 + i * 0.25, 1.5 + i * 0.25), { rot: 0.035 });
    });
  }
}

/* ---------- 5 降门槛 ---------- */
function card5(fr, lt) {
  bed(fr, IMG, 0.62, 1 + 0.06 * Math.min(1, lt / 4.4));
  // 从 features[2] 读，不再写死「全程不用改代码」
  const f = FEATURES[2];
  const t = String((typeof f === 'string') ? f : (f && (f.title || f.name)) || '');
  scrawl(fr, '第三个亮点', W / 2, 720, 84, 1, { rot: -0.04 });
  if (t) {
    const chars = Array.from(t);
    const per = Math.min(11, Math.ceil(chars.length / 2));
    const rows = [];
    for (let i = 0; i < chars.length; i += per) {
      rows.push(chars.slice(i, i + per).join(''));
    }
    rows.slice(0, 2).forEach((r, i) => {
      const size = r.length >= 10 ? 72 : 86;
      scrawl(fr, r, W / 2, 890 + i * 110, size,
             ss(lt, 0.5 + i * 0.25, 1.5 + i * 0.25), { rot: 0.03 });
    });
  }
}

/* ---------- 6 结论 ---------- */
function card6(fr, lt) {
  bed(fr, IMG, 0.7, 1 + 0.06 * Math.min(1, lt / 4.4));
  const concl = (CT.conclusion || ['完全开源', '拿来就用', '实用性拉满']).slice(0, 3);
  concl.forEach((t, i) => {
    const a = i === 0 ? 1 : ss(lt, 0.25 + i * 0.6, 0.25 + i * 0.6 + 0.9);
    if (a <= 0.003) return;
    scrawl(fr, String(t).slice(0, 10), W / 2, 660 + i * 180, 100, a,
           { rot: i % 2 ? 0.03 : -0.035 });
  });
  if (REPO) {
    fr.text(REPO, W / 2, 1330, {
      font: 'mono', size: 26, color: '#777777', a: ss(lt, 2.1, 2.8),
    });
  }

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

  // 垫一条深色带，浅色截图上字幕才不糊
  fr.rect(W / 2 - 480, 1330 - size * 0.9, 960, size * 1.8, {
    fill: '#000000', a: a * 0.6,
  });
  fr.text(s.zh, W / 2, 1330, {
    font: 'sans', size, color: '#FFFFFF', a,
    shadow: 0.95, shadowBlur: 10,
  });
}

const CUES = [
  [T.cover, 'rise'], [T.c1, 'thud'], [T.c2, 'tick'], [T.c3, 'tick'],
  [T.c4, 'tick'], [T.c5, 'tick'], [T.c6, 'chord', { root: 7 }],
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
  meta: { root: 0, drone: 0.4 },
  draw(fr, t) {
    fr.look.bgo = { color: BG };
    fr.look.bloom = 0.04;
    fr.look.grain = 0.05;

    const segs = [
      [0, T.c1, cover],
      [T.c1, T.c2, card1], [T.c2, T.c3, card2], [T.c3, T.c4, card3],
      [T.c4, T.c5, card4], [T.c5, T.c6, card5], [T.c6, DUR, card6],
    ];

    segs.forEach(sg => cut(fr, t, sg[0], sg[1], sg[2]));

    /* 鼠标光标：让静态截图有"被操作"的感觉。
     * 参考视频里都有 —— 观众看到光标动，才知道这是真在演示，
     * 不是 PPT 放了一张图。
     *
     * 三个动作：
     *   1. 封面卡：从右下角移到 Star 数那里，点一下
     *   2. 第三张卡：移到截图中间偏上
     */
    cursor(fr, t, 0.8, 1.2, W * 0.86, H * 0.60, W * 0.865, H * 0.402, 0.85);
    cursor(fr, t, 14.0, 1.4, W * 0.20, H * 0.70, W * 0.62, H * 0.40, 1.0);

    subtitles(fr, t);

    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    fr.text(timecode(t), 40, H - 34, {
      font: 'mono', size: 16, color: '#3A3A3A',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'l',
    });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
