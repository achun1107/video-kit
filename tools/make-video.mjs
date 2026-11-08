#!/usr/bin/env node
/**
 * make-video.mjs —— 一条命令：GitHub 仓库 → 成片
 *
 *   node tools/make-video.mjs --repo https://github.com/owner/name --out ./my-video
 *   node tools/make-video.mjs --repo <本地目录> --out ./my-video --skip-render
 *
 * 九步：
 *   0. 铺引擎骨架（engine/ + tools/ + 字体 + index.html）
 *   1. 仓库就位（URL 浅克隆 / 本地目录直接用）
 *   2. 抽内容        → content.json + content.js
 *   3. 截 GitHub 页  → assets/repo.png
 *   4. 生成配音      → audio/vo1.mp3 + vo1.srt（edge-tts）
 *   5. 字幕表        → audio/subs.json + subs.js
 *   6. 铺影片        → tools/film-template.js → film.js
 *   7. 渲染画面      → renders/raw.mp4
 *   8. 配乐 + 混音   → renders/final.mp4
 *   9. 播放页        → renders/player.html（DSH 内直接播）
 *
 * 文案在 audio/copy.json，第一次跑自动生成默认版本，改完再跑即可。
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, readdirSync } from 'node:fs';
import { join, basename, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const KIT = resolve(HERE, '..');

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : def;
}
const has = n => process.argv.includes(n);

const repoArg = arg('--repo');
const douyinInput = arg('--douyin');
let douyinAsr = null;   // 抖音流程的转写结果，用来生成参考稿
const videoArg = arg('--video');   // 任意站点视频链接，或本地文件
if (!repoArg && !douyinInput && !videoArg) {
  console.error('用法:');
  console.error('  node tools/make-video.mjs --repo <github url|本地目录> --out <工程目录>');
  console.error('  node tools/make-video.mjs --douyin <抖音分享链接> --out <工程目录>');
  console.error('  node tools/make-video.mjs --video <任意视频链接|本地文件> --out <工程目录>');
  console.error('可选: [--skip-render] [--reset-film] [--reset-html] [--music mp3] [--asr-model small]');
  process.exit(2);
}
const out = resolve(arg('--out', './video-out'));
const skipRender = has('--skip-render');

const PY = process.env.PYTHON || 'python';
const run = (cmd, args, opts = {}) => {
  console.log(`\n$ ${cmd} ${args.join(' ')}`);
  execFileSync(cmd, args, { stdio: 'inherit', cwd: out, ...opts });
};
const step = (n, title) => console.log(`\n${'='.repeat(56)}\n  ${n}. ${title}\n${'='.repeat(56)}`);

mkdirSync(out, { recursive: true });
for (const d of ['audio', 'assets', 'renders', 'review', 'tools', 'engine']) {
  mkdirSync(join(out, d), { recursive: true });
}

/* ══ 0. 铺引擎骨架 ══ */
step(0, '准备工程骨架');

const copyIfMissing = (rel) => {
  const src = join(KIT, rel), dst = join(out, rel);
  if (!existsSync(dst) && existsSync(src)) {
    mkdirSync(dirname(dst), { recursive: true });
    copyFileSync(src, dst);
    console.log(`  + ${rel}`);
  }
};

for (const f of [
  'engine/vk.js', 'engine/vk-kit.js', 'engine/render.py', 'engine/audio.py', 'engine/get_fonts.py',
  'tools/extract-content.mjs', 'tools/shot-github.py', 'tools/tts.py', 'tools/mix.py',
  'tools/make-player-html.py', 'tools/film-template.js',
]) copyIfMissing(f);

/* 字体：缺了会让 document.fonts.ready 一直等不到 → 渲染超时 180s */
const kitFonts = join(KIT, 'engine', 'fonts');
const outFonts = join(out, 'engine', 'fonts');
mkdirSync(outFonts, { recursive: true });
if (existsSync(kitFonts)) {
  let n = 0;
  for (const f of readdirSync(kitFonts)) {
    const dst = join(outFonts, f);
    if (!existsSync(dst)) { copyFileSync(join(kitFonts, f), dst); n += 1; }
  }
  if (n) console.log(`  + engine/fonts/ (${n} 个字体文件)`);
}

/* index.html：用 tools/index.template.html（竖屏 VK_SIZE + content.js + subs.js）。
 * 不要从 engine/index.html 复制 —— 那份是横屏的，会让卡片内容空白、画幅变 16:9。 */
const idx = join(out, 'index.html');
if (!existsSync(idx) || has('--reset-html')) {
  const tpl = join(KIT, 'tools', 'index.template.html');
  if (!existsSync(tpl)) process.exit('缺少 tools/index.template.html');
  writeFileSync(idx, readFileSync(tpl, 'utf8'), 'utf8');
  console.log('  + index.html（竖屏模板）');
}

/* ══ 0.5 抖音链接：先下载原片、逆向、找仓库 ══ */
const douyinArg = arg('--douyin');
let repoArgFinal = repoArg;

/* ══ 0.4 通用视频：任意站点链接 / 本地文件 ══
 * 和抖音的区别：抖音要按点赞排序逐条试（一个主页链接含多个视频），
 * 这里给的就是一条视频的直链，直接下。
 * 平台支持由 yt-dlp 决定（1755 个站点，含 YouTube/B站/小红书/微博/TikTok）。
 */
if (videoArg && !douyinArg) {
  step(0.4, '视频：下载 + 转写 + 找仓库');
  const work = join(out, 'video');
  mkdirSync(work, { recursive: true });

  // 1) 下载（本地文件会直接复制）
  run(PY, [join(KIT, 'tools', 'video-download.py'), videoArg, '-o', work]);

  const mp4 = join(work, 'video.mp4');
  const srt = join(work, 'subs.srt');
  const asrOut = join(work, 'asr.json');

  if (!existsSync(mp4)) process.exit('× 视频没下载下来');

  // 2) 有站点字幕就转成 asr.json（省掉本地转写，而且更准）
  if (existsSync(srt)) {
    console.log('  用站点字幕（比本地转写准）');
    try {
      run(PY, [join(KIT, 'tools', 'srt-to-asr.py'), srt, '-o', asrOut]);
    } catch {
      console.log('  字幕解析失败，退回本地转写');
    }
  }

  // 3) 没有字幕才本地转写
  if (!existsSync(asrOut) || has('--reset-asr')) {
    run(PY, [join(KIT, 'tools', 'transcribe-local.py'), mp4,
             '--model', arg('--asr-model', 'small'), '--out', asrOut]);
  }

  // 4) 找仓库
  let videoTitle = '';
  try {
    const m = JSON.parse(readFileSync(join(work, 'meta.json'), 'utf8'));
    videoTitle = m.title || '';
  } catch { }

  const foundJson = join(work, 'found.json');
  try {
    run(PY, [join(KIT, 'tools', 'repo-finder.py'), asrOut,
             '--title', videoTitle, '-o', foundJson]);
  } catch {
    console.log('  （repo-finder 退出码非 0，多半是没把握）');
  }

  let videoRepo = null;
  try {
    const found = JSON.parse(readFileSync(foundJson, 'utf8'));
    if (found.confident && found.best) {
      videoRepo = found.best;
      console.log(`  ✓ 视频里讲的是：${videoRepo}`);
    } else {
      console.log('  没把握确定是哪个仓库');
      if (found.candidates && found.candidates.length) {
        console.log('  候选：' + found.candidates.slice(0, 3)
          .map(c => `${c.full_name}(${c.stars})`).join('  '));
      }
    }
  } catch { }

  if (!videoRepo && !has('--repo')) {
    process.exit('× 视频里没识别出仓库，用 --repo <owner/repo> 指定');
  }
  if (videoRepo) repoArgFinal = videoRepo;
  douyinAsr = asrOut;   // 复用参考稿逻辑
}

if (douyinArg) {
  step(0.5, '抖音：下载原视频并逆向');
  let resolved = {};
  const work = join(out, 'douyin');
  mkdirSync(work, { recursive: true });

  // 1) 抓视频列表（带点赞数和真实标题）
  const rankJson = join(work, 'rank.json');
  run(PY, [join(KIT, 'tools', 'douyin-rank.py'), douyinArg,
           '-o', rankJson, '--max', arg('--list-max', '20')]);
  let rank = { videos: [] };
  try { rank = JSON.parse(readFileSync(rankJson, 'utf8')); } catch { }
  if (!rank.videos || !rank.videos.length) {
    process.exit('× 抖音链接里没解析出视频');
  }

  // 选哪条：
  //   --video <id>  指定某条
  //   否则按点赞降序逐条试，选第一条能识别出仓库的（最多 --try 条，默认 4）
  // 为什么要逐条试：点赞最高的那条讲的是 ChatGPT 内置功能，压根没有 GitHub
  // 仓库，盲选第一条必然失败。
  const wantId = arg('--video');
  const maxTry = parseInt(arg('--try', '4'), 10) || 4;
  const pool = wantId
    ? rank.videos.filter(v => v.id === String(wantId)).concat(rank.videos)
    : rank.videos;
  const candidates = pool.slice(0, Math.max(1, maxTry));

  const dlDir = join(work, 'dl');
  mkdirSync(dlDir, { recursive: true });

  let repoFromVideo = null;
  let pick = null;
  let asrJson = null;

  for (let ci = 0; ci < candidates.length; ci += 1) {
    const v = candidates[ci];
    const dg = (v.digg || 0).toLocaleString();
    console.log(`\n  试 ${ci + 1}/${candidates.length}：${dg} 赞  ${String(v.title || '').slice(0, 34)}`);

    // 下载
    const mp4 = join(dlDir, `${v.id}.mp4`);
    if (!existsSync(mp4) && !has('--skip-download')) {
      try {
        run(PY, [join(KIT, 'tools', 'douyin-download.py'), v.id, '-o', dlDir]);
      } catch (e) {
        console.log('   下载失败');
      }
    }
    if (!existsSync(mp4)) {
      console.log('   没有文件，跳过');
      continue;
    }

    // 转写
    const aj = join(work, `asr-${v.id}.json`);
    if (!existsSync(aj) || has('--reset-asr')) {
      try {
        run(PY, [join(KIT, 'tools', 'transcribe-local.py'), mp4,
                 '--model', arg('--asr-model', 'small'), '--out', aj]);
      } catch (e) {
        console.log('   转写失败');
      }
    }
    if (!existsSync(aj)) {
      console.log('   没有转写结果，跳过');
      continue;
    }

    // 找仓库
    const fj = join(work, `found-${v.id}.json`);
    try {
      run(PY, [join(KIT, 'tools', 'repo-finder.py'), aj, '--title', v.title || '', '-o', fj]);
    } catch (e) {
      // repo-finder 没把握时退出码是 1，正常
    }
    let found = {};
    try { found = JSON.parse(readFileSync(fj, 'utf8')); } catch { }

    if (found.confident && found.best) {
      repoFromVideo = found.best;
      pick = v;
      asrJson = aj;
      console.log(`   ✓ 视频里讲的是：${repoFromVideo}`);
      break;
    }
    if (found.candidates && found.candidates.length) {
      console.log('   候选：' + found.candidates.slice(0, 2)
        .map(c => `${c.full_name}(${c.stars})`).join('  '));
    }
    console.log('   没把握，换下一条');
  }

  if (!pick) {
    if (has('--repo')) {
      console.log('  候选都没识别出仓库，按 --repo 指定的继续');
    } else {
      process.exit(`× 前 ${candidates.length} 条都没识别出仓库。用 --repo <owner/repo> 指定，或 --video <id> 选一条`);
    }
  }
  if (pick) {
    console.log(`\n  选中：${pick.id}  ${pick.url}`);
    resolved.title = pick.title;
  }
  if (repoFromVideo) repoArgFinal = repoFromVideo;
  // 把转写路径存到外层，等 content.json 生成后再用它写参考稿
  if (asrJson) douyinAsr = asrJson;

  // 5) 用 API 直接生成 content.json（大仓库 clone 会超时）
  if (!has('--repo') || repoFromVideo) {
    try {
      run(PY, [join(KIT, 'tools', 'repo-content.py'), repoArgFinal,
               '-o', join(out, 'content.json'),
               ...(process.env.GITHUB_TOKEN ? ['--token', process.env.GITHUB_TOKEN] : [])]);
    } catch (e) {
      console.warn('  API 抽内容失败，退回 clone：', e.message);
    }
  }
}

/* ══ 1. 仓库就位 ══ */
step(1, '仓库就位');
let repoDir = null;
if (/^https?:\/\//.test(repoArgFinal) || repoArgFinal.startsWith('git@')) {
  const name = basename(repoArgFinal).replace(/\.git$/, '');
  repoDir = join(out, '_repos', name);
  mkdirSync(dirname(repoDir), { recursive: true });
  if (existsSync(join(repoDir, '.git'))) {
    try { execFileSync('git', ['-C', repoDir, 'fetch', '--depth', '1', 'origin'], { stdio: 'ignore' }); } catch { }
    console.log(`  用已有副本 ${repoDir}`);
  } else {
    console.log(`  浅克隆 ${repoArgFinal}`);
    try {
      execFileSync('git', ['-c', 'credential.helper=', 'clone', '--depth', '1', repoArg, repoDir],
                   { cwd: out, stdio: 'inherit', timeout: 180000 });
    } catch {
      console.warn('  克隆失败 → content.json 需要手工填');
      repoDir = null;
    }
  }
} else {
  repoDir = resolve(repoArgFinal);
  console.log(`  本地目录 ${repoDir}`);
}

/* ══ 2. 抽内容 ══ */
step(2, '抽内容');
if (repoDir && existsSync(repoDir)) {
  try {
    run(process.execPath, [join(out, 'tools', 'extract-content.mjs'), repoDir, '-o', join(out, 'content.json')]);
  } catch {
    console.warn('  抽取失败，写占位 content.json');
  }
}
if (!existsSync(join(out, 'content.json'))) {
  writeFileSync(join(out, 'content.json'), JSON.stringify({
    repo: basename(repoArgFinal).replace(/\.git$/, ''), namePlain: '这个项目',
    emoji: '📦', headline: '一个值得看的开源项目', tagline: '', version: '',
    stats: {}, features: [], chapters: [],
  }, null, 2), 'utf8');
}
const content = JSON.parse(readFileSync(join(out, 'content.json'), 'utf8'));
writeFileSync(join(out, 'content.js'), 'window.CONTENT = ' + JSON.stringify(content, null, 2) + ';\n', 'utf8');
console.log(`  ${content.namePlain || content.name} / ${content.headline || ''}`);

/* ══ 3. 截图 ══ */
step(3, '截 GitHub 截图');
try {
  const url = /^https?:\/\//.test(repoArgFinal)
    ? repoArgFinal.replace(/\.git$/, '')
    : `https://github.com/${content.repo || basename(repoArgFinal)}`;
  run(PY, [join(out, 'tools', 'shot-github.py'), url, '-o', join(out, 'assets', 'repo.png'),
           '--mode', 'viewport', '--height', '1100']);
} catch {
  console.warn('  截图失败（没有也能出片）');
}

/* ══ 4-5. 配音 + 字幕 ══ */
/* 有抖音转写时先写参考稿 —— 借原片的话术骨架，比模板稿信息密度高得多。
 * 必须在 content.json 生成之后（第 2 步）、配音之前（第 4 步）。 */
if (douyinAsr && existsSync(douyinAsr)) {
  try {
    run(PY, [join(KIT, 'tools', 'script-writer.py'), out,
             '--from-asr', douyinAsr, '--style', 'reference']);
    console.log('  ✓ 已用原片话术生成参考稿（建议看一遍再出片）');
  } catch {
    console.log('  参考稿生成失败，退回模板稿');
  }
}

step(4, '生成配音与字幕');
const copyPath = join(out, 'audio', 'copy.json');
if (!existsSync(copyPath)) {
  const nm = content.namePlain || content.name || '这个项目';
  const tag = String(content.tagline || '一个开源项目').replace(/[。！？，、；：]+$/, '');
  writeFileSync(copyPath, JSON.stringify({
    voice: 'zh-CN-YunxiNeural', rate: '+45%', pitch: '+5Hz',
    vo1_at: 0.6, vo2_at: 21.1,
    vo1: `${tag}。这个叫${nm}的开源项目，把最要紧的东西都摆出来了。先从它是什么讲起，再一条条拆给你看。不用注册，不用订阅，装好就能用。`,
    vo2: '它不只会讲，还能直接上手。完全免费、完全开源。不知道从哪开始，照着仓库里的说明走就行。',
    _note: '改完这个文件重跑 make-video.mjs 即可',
  }, null, 2), 'utf8');
  console.log(`  已生成默认文案 ${copyPath}（建议改完再跑一次）`);
}
try {
  run(PY, [join(out, 'tools', 'tts.py'), out]);
} catch (e) {
  console.warn('  配音失败：', e.message);
}

/* ══ 6. 铺影片 ══ */
step(5, '铺影片模板');
if (!existsSync(join(out, 'film.js')) || has('--reset-film')) {
  copyFileSync(join(out, 'tools', 'film-template.js'), join(out, 'film.js'));
  console.log('  film.js ← tools/film-template.js');
} else {
  console.log('  film.js 已存在，保留（--reset-film 覆盖）');
}

if (skipRender) {
  console.log('\n--skip-render：内容、配音、模板就位，渲染跳过。');
  process.exit(0);
}

/* ══ 7. 渲染 ══ */
step(6, '渲染画面');
run(PY, [join(out, 'engine', 'render.py'), out]);

/* ══ 8. 配乐 + 混音 ══ */
step(7, '配乐与混音');
try {
  run(PY, [join(out, 'engine', 'render.py'), out, '--events']);
  run(PY, [join(out, 'engine', 'audio.py'), out, '--wav-only']);
} catch (e) {
  console.warn('  配乐失败（继续）：', e.message);
}
const tlPath = join(out, 'audio', 'timeline.json');
const tl = existsSync(tlPath) ? JSON.parse(readFileSync(tlPath, 'utf8')) : {};
const vo1at = tl.vo1_at != null ? tl.vo1_at : 0.6;
const vo2at = tl.vo2_at != null ? tl.vo2_at : 21.1;
const bgm = arg('--music', join(KIT, '..', 'video-xiaobai', 'audio', 'bgm', 'Carefree.mp3'));
const mixArgs = [join(out, 'tools', 'mix.py'), out,
  '--vo1', String(vo1at), '--vo2', String(vo2at),
  '--bg', '0.06', '--music-gain', '0.075', '--vo-gain', '2.0', '--lufs', '-13'];
if (existsSync(bgm)) mixArgs.push('--music', bgm);
try {
  run(PY, mixArgs);
} catch (e) {
  console.warn('  混音失败（保留无声版）：', e.message);
}

/* ══ 9. 播放页 ══ */
step(8, '生成播放页');
try {
  run(PY, [join(out, 'tools', 'make-player-html.py'), join(out, 'renders', 'final.mp4'),
           '-o', join(out, 'renders', 'player.html'), '--crf', '29']);
} catch (e) {
  console.warn('  播放页失败：', e.message);
}

const final = join(out, 'renders', 'final.mp4');
console.log(`\n${'='.repeat(56)}`);
if (existsSync(final)) {
  console.log(`✓ 成片 → ${final}`);
  console.log(`  播放页 → ${join(out, 'renders', 'player.html')}`);
} else {
  console.log(`完成画面 → ${join(out, 'renders', 'raw.mp4')}`);
}
console.log('='.repeat(56));
