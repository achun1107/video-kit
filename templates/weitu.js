/* 风格 D：全屏演示（参考 weitu / 喂兔）
 *
 * 原视频只有 9.5 秒且转写空白，数据不完整。
 * 这套是按标题「AI 自己操控电脑，github 上火了，不用截图」推断的：
 *   · 全屏真实画面，不做截图框
 *   · 极简文字叠加（不多说，让画面说话）
 *   · 上下留黑边（像电影画幅），文字压在黑边里
 *   · 节奏慢，一句停留 5 秒以上
 *
 * ⚠️ 这是**推断版**，不是从原片逆向出来的。原片数据拿到后应重做。
 */
const { W, H, clamp, seg, ss, hash, lerp, E } = VK;

const CT = window.CONTENT || {};
const NAME = CT.namePlain || CT.name || '这个项目';
const HEAD = (CT.headline || '').trim();
const STATS = CT.stats || {};
const FEATURES = CT.features || [];
const REPO = CT.repo || '';

const DUR = 34.8;

const BG = '#000000';
const FG = '#FFFFFF';
const DIM = '#7A7A7A';
const ACCENT = '#00E0A4';

/* 电影画幅：上下各留 260px 黑边 */
const BAND = 260;

const T = {
  c1: 1.0, c2: 6.0, c3: 11.5, c4: 17.5, c5: 23.5, c6: 29.0,
  outro: DUR - 2.0,
};

const SUBS = window.SUBS || [];

const pad2 = n => String(n).padStart(2, '0');
function timecode(t) {
  const s = Math.max(0, t), m = Math.floor(s / 60), s2 = Math.floor(s % 60),
        ms = Math.floor((s % 1) * 1000);
  return `${pad2(m)}:${pad2(s2)}.${String(ms).padStart(3, '0')}`;
}

const IMG = new Image();
IMG.src = 'assets/repo.png';
window.__IMAGES = [IMG];

/* 全屏画面：裁掉上下，铺满中间区域 */
function scene(fr, k) {
  const bh = H - BAND * 2;
  if (!IMG.complete || !IMG.naturalWidth) {
    fr.rect(0, BAND, W, bh, { fill: '#111111' });
    return;
  }
  const ctx = fr.x;
  const sc = 1.06 + 0.1 * k;
  const w = W * sc;
  const h = w * IMG.naturalHeight / IMG.naturalWidth;
  const dx = (W - w) / 2;
  const dy = BAND + (bh - h) / 2;

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, BAND, W, bh);
  ctx.clip();
  ctx.drawImage(IMG, dx, dy, w, h);
  ctx.restore();
}

/* 黑边里的文字：左对齐，小号，像片头字幕 */
function line(fr, text, x, y, size, a, col) {
  if (a <= 0.003) return;
  fr.text(text, x, y, {
    font: 'sans', size, color: col || FG, a, align: 'l',
  });
}

/* 一条极细的强调线 */
function rule(fr, x, y, maxW, k, col) {
  if (k <= 0.003) return;
  fr.rect(x, y, maxW * Math.min(1, k), 2, { fill: col || ACCENT, a: 0.9 });
}

/* ---------- 1 片头 ---------- */
function card1(fr, lt) {
  scene(fr, ss(lt, 0, 3.5));

  const a1 = ss(lt, 0.2, 1.4);
  line(fr, NAME, 90, BAND - 96, 64, a1);
  rule(fr, 90, BAND - 60, 300, ss(lt, 0.7, 1.7));

  if (HEAD) {
    const a2 = ss(lt, 1.2, 2.4);
    line(fr, HEAD.slice(0, 18), 90, H - BAND + 96, 44, a2, DIM);
  }
}

/* ---------- 2 star ---------- */
function card2(fr, lt) {
  scene(fr, 0.5 + ss(lt, 0, 3.0) * 0.5);

  const star = STATS.star;
  if (!star) {
    line(fr, '完全开源', 90, BAND - 90, 56, ss(lt, 0.2, 1.4));
    return;
  }
  const k = ss(lt, 0.2, 1.8);
  const shown = Math.round(star * E.out3(k));
  fr.text(shown.toLocaleString('en-US'), 90, H - BAND + 180, {
    font: 'sans', size: 150, color: ACCENT,
    a: Math.min(1, k * 1.8), align: 'l',
  });
  line(fr, 'STAR', 90, H - BAND + 110, 30, ss(lt, 1.0, 1.8), DIM);
}

/* ---------- 3 一句卖点 ---------- */
function card3(fr, lt) {
  scene(fr, 1.0);

  const chars = Array.from(HEAD || '一个值得看看的开源项目');
  const rows = [];
  for (let i = 0; i < chars.length && rows.length < 3; i += 14) {
    rows.push(chars.slice(i, i + 14).join(''));
  }
  rows.forEach((r, i) => {
    const a = ss(lt, 0.3 + i * 0.7, 0.3 + i * 0.7 + 1.2);
    line(fr, r, 90, BAND - 150 + i * 96, 64, a);
  });
}

/* ---------- 4 三个特性（竖排，左侧对齐）---------- */
function card4(fr, lt) {
  scene(fr, 1.5);

  const list = FEATURES.slice(0, 3).map(f =>
    String((typeof f === 'string') ? f : (f.title || f.name || '')).slice(0, 12));
  const rows = list.length ? list : ['开箱即用', '零配置', '完全开源'];

  rows.forEach((t, i) => {
    const a = ss(lt, 0.4 + i * 0.95, 0.4 + i * 0.95 + 1.1);
    if (a <= 0.003) return;
    const y = BAND - 190 + i * 200;
    fr.text('0' + (i + 1), 90, y, {
      font: 'mono', size: 24, color: ACCENT, a: a * 0.85, align: 'l',
    });
    line(fr, t, 90, y + 48, 58, a);
    rule(fr, 90, y + 118, 240, ss(lt, 0.4 + i * 0.95 + 0.5, 0.4 + i * 0.95 + 1.3), DIM);
  });
}

/* ---------- 5 画面细节 ---------- */
function card5(fr, lt) {
  scene(fr, 1.0 + ss(lt, 0, 3.0) * 0.5);

  const a = ss(lt, 0.8, 1.8);
  line(fr, '这个界面', 90, H - BAND + 130, 40, a, DIM);
  rule(fr, 90, H - BAND + 168, 180, ss(lt, 1.2, 2.0));
}

/* ---------- 6 结论 ---------- */
function card6(fr, lt) {
  scene(fr, 2.0);

  const concl = (CT.conclusion || ['完全开源', '拿来就用', '很实用']).slice(0, 3);
  concl.forEach((t, i) => {
    const a = ss(lt, 0.3 + i * 0.8, 0.3 + i * 0.8 + 1.1);
    if (a <= 0.003) return;
    line(fr, String(t).slice(0, 10), 90, BAND - 130 + i * 120, 68, a,
         i === concl.length - 1 ? ACCENT : FG);
  });

  if (REPO) {
    fr.text(REPO, 90, H - BAND + 180, {
      font: 'mono', size: 24, color: DIM, a: ss(lt, 2.2, 2.9), align: 'l',
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
  const size = Math.min(48, Math.round(860 / (vw * 1.0)));

  // 字幕压在下黑边里，不挡画面
  fr.text(s.zh, W / 2, H - BAND + 200, {
    font: 'sans', size, color: FG, a: a * 0.9,
  });
}

const CUES = [
  [T.c1, 'rise'], [T.c2, 'chord', { root: 0 }], [T.c3, 'soft'],
  [T.c4, 'tick'], [T.c5, 'soft'], [T.c6, 'chord', { root: 7 }],
  [DUR - 1.2, 'hush'],
];

VK.film({
  dur: DUR, fps: 30, theme: 'flat',
  meta: { root: 0, drone: 0.38 },
  draw(fr, t) {
    fr.look.bgo = { color: BG };
    fr.look.bloom = 0.03;
    fr.look.grain = 0.04;

    const segs = [
      [T.c1, T.c2, card1], [T.c2, T.c3, card2], [T.c3, T.c4, card3],
      [T.c4, T.c5, card4], [T.c5, T.c6, card5], [T.c6, DUR, card6],
    ];

    segs.forEach(sg => {
      const a = sg[0], b = sg[1], fn = sg[2];
      if (t < a || t >= b) return;
      const kk = Math.min(seg(t, a, a + 0.05), 1 - seg(t, b - 0.04, b));
      if (kk <= 0.002) return;
      fr.g({ a: kk }, () => fn(fr, t - a));
    });

    subtitles(fr, t);

    for (let i = 0; i < CUES.length; i++) {
      const tt = CUES[i][0];
      if (t >= tt && t < tt + 0.034) fr.sfx(tt, CUES[i][1], CUES[i][2] || {});
    }

    fr.text(timecode(t), W - 40, H - 34, {
      font: 'mono', size: 16, color: '#333333',
      a: ss(t, 0.5, 1.2) * 0.8, align: 'r',
    });

    const ko = ss(t, T.outro, DUR);
    if (ko > 0) fr.flash(ko * 0.05, '#000000');
  },
});
