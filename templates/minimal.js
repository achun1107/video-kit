/* 极简文字风 —— 第二套模板
 *
 * 和 tech 模板（深底 + 白卡 + 橙色强调）的区别：
 *   tech    卡片、边框、色彩块，信息密度高，像产品页
 *   极简    纯黑底、无卡片、大字居中，一句一行，像演讲稿
 *
 * 接口和 tech 完全一致：读 window.CONTENT / window.SUBS，调 VK.film。
 * 换风格只改 film.js 文件，content.json 和 copy.json 不动。
 *
 * 硬约束（和所有模板一样）：
 *   · 画面是 t 的纯函数，不能用 Math.random() / Date.now() / 跨帧状态
 *   · 不用 ctx.shadow*（破坏 --det）
 *   · 多图合成先烤离屏 canvas
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const TAG = (CT.tagline || '').trim();
const REPO = CT.repo || '';
const VER = CT.version || '';
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const ITEMS = CT.chapters || CT.palettes || [];
const CONCL = CT.conclusion || [];

/* 极简风配色：只有一个强调色，其余全靠黑白灰对比 */
const BG = '#000000';
const FG = '#FFFFFF';
const DIM = '#5A5A5A';
const ACCENT = CT.accent || '#FF3B30';

const DUR = 34.8;

/* 时间轴：比 tech 模板稀疏，每段停留更久，配合"一句一行"的节奏 */
const T = {
  head: 0.3,
  c1: 1.2,    // 项目名巨大
  c2: 6.0,    // 一句话卖点
  c3: 10.5,   // 数字
  c4: 15.0,   // 三条特性
  c5: 21.5,   // 截图
  c6: 26.5,   // 清单
  c7: 30.5,   // 结论
  outro: DUR - 2.2,
};

const SUBS = window.SUBS || [];

/* ---------- 工具 ---------- */
const pad2 = n => String(n).padStart(2, '0');

function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

/* 极简风的核心：一句一行地"打"出来，不是淡入，是逐字出现 */
function typeline(fr, text, y, size, a, col) {
  if (a <= 0.003) return;
  const total = Array.from(text).length;
  const show = Math.max(0, Math.min(total, Math.floor(a * total * 1.35)));
  const shown = Array.from(text).slice(0, show).join('');
  if (!shown) return;
  fr.text(shown, W / 2, y, {
    font: 'sans', size, color: col || FG, a: Math.min(1, a * 1.4),
  });
}

/* 一条会"生长"的细线，当作进度/装饰 */
function growLine(fr, x, y, maxW, k, col) {
  if (k <= 0.003) return;
  const w = maxW * Math.min(1, k);
  fr.rect(x, y, w, 2, { fill: col || ACCENT, a: 0.9 });
}

/* 编号（01 / 02 / 03），极小，靠上 */
function num(fr, n, x, y, a) {
  fr.text(String(n).padStart(2, '0'), x, y, {
    font: 'mono', size: 20, color: DIM, a: a * 0.85, align: 'l',
  });
}

/* ---------- 素材 ---------- */
const REPO_IMG = new Image();
REPO_IMG.src = 'assets/repo.png';
window.__IMAGES = [REPO_IMG];

function shot(fr, img, x, y, w, o) {
  o = o || {};
  if (!img || !img.complete || !img.naturalWidth) {
    fr.rect(x, y, w, w * 0.55, { fill: '#141414' });
    return 0;
  }
  const h = w * img.naturalHeight / img.naturalWidth;
  const ctx = fr.x;
  ctx.save();
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, o.r || 4); else ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
  return h;
}

/* ---------- 1 项目名巨大 ---------- */
function card1(fr, lt) {
  const k = ss(lt, 0.15, 1.1);
  if (k <= 0) return;

  // 名字：从大到"落定"，带一点缩放
  const sc = 1 + (1 - k) * 0.14;
  const size = Math.round(150 * sc);
  fr.text(NAME, W / 2, 760, {
    font: 'sans', size, color: FG, a: k,
    align: 'c',
  });

  // 名字下一条生长的线
  growLine(fr, W / 2 - 200, 850, 400, ss(lt, 0.7, 1.6));

  // 版本号，极小
  if (VER) {
    fr.text('v' + VER, W / 2, 900, {
      font: 'mono', size: 20, color: DIM, a: ss(lt, 1.4, 1.9),
    });
  }
}

/* ---------- 2 一句话卖点 ---------- */
function card2(fr, lt) {
  const line = HEAD || TAG || '一个值得看看的开源项目';

  num(fr, 1, 110, 300, ss(lt, 0.1, 0.5));

  // 断行要分语言：
  //   中文按字符数平分（一个字一个单位，随便断不影响可读性）
  //   英文必须按空格断词 —— 按字符断会切出 "Render v / ideo" 这种
  const isLatin = /^[\x20-\x7E]+$/.test(line.trim());
  let l1 = '', l2 = '';

  if (isLatin) {
    const words = line.trim().split(/\s+/);
    const mid = Math.ceil(words.length / 2);
    l1 = words.slice(0, mid).join(' ');
    l2 = words.slice(mid).join(' ');
  } else {
    const chars = Array.from(line);
    const half = Math.ceil(chars.length / 2);
    l1 = chars.slice(0, half).join('');
    l2 = chars.slice(half).join('');
  }

  // 英文用更小字号 —— 同样的 size 下英文字宽是中文的 2 倍，会顶出画面
  const size = isLatin ? 62 : 88;

  const a1 = ss(lt, 0.2, 1.5);
  typeline(fr, l1, 720, size, a1, FG);
  if (l2) {
    const a2 = ss(lt, 0.9, 2.2);
    typeline(fr, l2, 830, size, a2, FG);
  }

  growLine(fr, 110, 980, 300, ss(lt, 1.6, 2.6));
}

/* ---------- 3 数字 ---------- */
function card3(fr, lt) {
  const star = STATS.star || 0;
  num(fr, 2, 110, 300, ss(lt, 0.1, 0.5));

  if (!star) {
    typeline(fr, '完全开源', 780, 110, ss(lt, 0.3, 1.6), FG);
    return;
  }

  // 数字滚上去（E.out3 是三次缓出，VK 里的命名是 out3 不是 outCubic）
  const k = ss(lt, 0.3, 1.8);
  const shown = Math.round(star * E.out3(k));
  fr.text(shown.toLocaleString('en-US'), W / 2, 740, {
    font: 'sans', size: 200, color: ACCENT, a: Math.min(1, k * 2),
  });

  fr.text('STAR', W / 2, 880, {
    font: 'mono', size: 28, color: DIM, a: ss(lt, 1.2, 1.8),
  });

  growLine(fr, 110, 960, W - 220, ss(lt, 1.6, 2.8));
}

/* ---------- 4 三条特性 ---------- */
function card4(fr, lt) {
  num(fr, 3, 110, 300, ss(lt, 0.1, 0.5));

  const list = FEATURES.slice(0, 3);
  const rows = list.length ? list.map(f => {
    const t = (typeof f === 'string') ? f : (f.title || f.name || '');
    return String(t).slice(0, 14);
  }) : ['完全开源', '开箱即用', '零依赖'];

  rows.forEach((t, i) => {
    const a = ss(lt, 0.4 + i * 0.85, 0.4 + i * 0.85 + 1.2);
    const y = 640 + i * 170;
    if (a <= 0.003) return;

    // 大号数字当序号
    fr.text('0' + (i + 1), 110, y + 42, {
      font: 'sans', size: 54, color: ACCENT, a: a * 0.9, align: 'l',
    });
    typeline(fr, t, y + 30, 76, a, FG);
  });
}

/* ---------- 5 截图 ---------- */
function card5(fr, lt) {
  num(fr, 4, 110, 300, ss(lt, 0.1, 0.5));

  const k = ss(lt, 0.2, 1.4);
  const w = 860 * (0.94 + 0.06 * k);
  const x = (W - w) / 2;
  const y = 460 + (1 - k) * 40;

  if (k > 0.003) {
    fr.g({ a: Math.min(1, k * 1.3) }, () => shot(fr, REPO_IMG, x, y, w, { r: 4 }));
  }

  const la = ss(lt, 1.2, 2.0);
  fr.text('GitHub 上，代码全公开', W / 2, 1320, {
    font: 'sans', size: 34, color: DIM, a: la,
  });
}

/* ---------- 6 清单 ---------- */
function card6(fr, lt) {
  num(fr, 5, 110, 300, ss(lt, 0.1, 0.5));

  const list = ITEMS.slice(0, 5);
  const names = list.length
    ? list.map(it => String((typeof it === 'string') ? it : (it.title || it.name || '')).slice(0, 12))
    : ['第一步', '第二步', '第三步'];

  names.forEach((t, i) => {
    const a = ss(lt, 0.3 + i * 0.55, 0.3 + i * 0.55 + 1.0);
    if (a <= 0.003) return;
    const y = 600 + i * 150;

    // 编号 + 细线 + 文字，一行一件事
    fr.text(String(i + 1), 110, y + 14, {
      font: 'mono', size: 30, color: ACCENT, a: a * 0.9, align: 'l',
    });
    typeline(fr, t, y, 60, a, FG);
    growLine(fr, 110, y + 70, 240, ss(lt, 0.3 + i * 0.55 + 0.6, 0.3 + i * 0.55 + 1.4), DIM);
  });
}

/* ---------- 7 结论 ---------- */
function card7(fr, lt) {
  const lines = (CONCL.length ? CONCL : ['完全开源', '拿来就用', '三分钟上手']).slice(0, 3);

  // 三条结论竖排，最后一条用强调色
  lines.forEach((t, i) => {
    const a = ss(lt, 0.2 + i * 0.6, 0.2 + i * 0.6 + 1.1);
    if (a <= 0.003) return;
    const isLast = i === lines.length - 1;
    typeline(fr, String(t).slice(0, 12), 660 + i * 150, 96, a,
             isLast ? ACCENT : FG);
  });

  growLine(fr, W / 2 - 120, 1160, 240, ss(lt, 1.8, 2.6));

  if (REPO) {
    fr.text(REPO, W / 2, 1240, {
      font: 'mono', size: 24, color: DIM, a: ss(lt, 2.0, 2.7),
    });
  }
}

/* ---------- 字幕：极简风下用细描边，不用投影 ---------- */
function subtitles(fr, t) {
  if (!SUBS.length) return;
  const cand = SUBS.filter(x => t >= x.a - 0.05 && t <= x.b + 0.25);
  const s = cand.length ? cand[cand.length - 1] : null;
  if (!s) return;

  const a = ss(t, s.a, s.a + 0.16) * (1 - ss(t, s.b, s.b + 0.1));
  if (a <= 0.003) return;

  const vw = Array.from(s.zh).reduce(
    (n, ch) => n + (/[\u4e00-\u9fff]/.test(ch) ? 1 : (ch === ' ' ? 0.3 : 0.56)), 0);
  const size = Math.min(60, Math.round(860 / (vw * 1.0)));

  fr.text(s.zh, W / 2, 1560, {
    font: 'sans', size, color: FG, a: a * 0.95,
    shadow: 0.7, shadowBlur: 6,
  });
}

/* ---------- 音效 ---------- */
const CUES = [
  [T.c1, 'soft'], [T.c2, 'tick'], [T.c3, 'chord', { root: 5 }],
  [T.c4, 'tick'], [T.c5, 'soft'], [T.c6, 'tick'], [T.c7, 'chord', { root: 7 }],
  [DUR - 1.2, 'hush'],
];

/* ---------- 主绘制 ---------- */
VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.42 },
  draw(fr, t) {
    fr.look.bgo = { color: BG };
    fr.look.bloom = 0.04;
    fr.look.grain = 0.035;

    /* 背景：极简风的呼吸感靠两条很淡的横向光带 */
    fr.look.under = (ctx, tt) => {
      ctx.save();
      for (let i = 0; i < 2; i++) {
        const y = H * (0.28 + i * 0.44) + Math.sin(tt * 0.22 + i * 1.7) * 24;
        const g = ctx.createLinearGradient(0, y - 120, 0, y + 120);
        g.addColorStop(0, 'rgba(255,255,255,0)');
        g.addColorStop(0.5, `rgba(255,255,255,${0.018 + i * 0.008})`);
        g.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0, y - 120, W, 240);
      }
      ctx.restore();
    };

    /* 顶部一条细进度线，极简风唯一的"界面元素" */
    fr.rect(0, 0, W, 3, { fill: ACCENT, a: 0.75 });
    fr.rect(0, 0, W * (t / DUR), 3, { fill: FG, a: 0.45 });

    /* 七段 */
    const segs = [
      [T.c1, T.c2, card1],
      [T.c2, T.c3, card2],
      [T.c3, T.c4, card3],
      [T.c4, T.c5, card4],
      [T.c5, T.c6, card5],
      [T.c6, T.c7, card6],
      [T.c7, DUR, card7],
    ];

    segs.forEach(sg => {
      const a = sg[0], b = sg[1], fn = sg[2];
      if (t < a || t >= b) return;
      const kk = Math.min(seg(t, a, a + 0.05), 1 - seg(t, b - 0.04, b));
      if (kk <= 0.002) return;
      fr.g({ a: kk }, () => fn(fr, t - a));
    });

    subtitles(fr, t);

    /* 音效 */
    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    /* 时间码，极小，左下 */
    fr.text(timecode(t), 40, H - 36, {
      font: 'mono', size: 16, color: '#333333',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'l',
    });

    /* 结尾淡出 */
    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
