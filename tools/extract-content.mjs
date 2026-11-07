#!/usr/bin/env node
/**
 * extract-content.mjs — 把一个仓库的「可拍内容」抽成 content.json
 *
 *   node tools/extract-content.mjs <仓库目录> [-o content.json]
 *
 * 读 index.md / README.md / catalog.md，抽出：
 *   name / headline / tagline / chapters[] / features[] / repo
 * 不做模型调用，纯规则解析，换任何 VitePress 风格的知识站都能用。
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';

const dir = process.argv[2];
if (!dir) { console.error('用法: node extract-content.mjs <仓库目录> [-o 输出]'); process.exit(2); }
const outIdx = process.argv.indexOf('-o');
const out = outIdx > 0 ? process.argv[outIdx + 1] : join(dir, 'content.json');

const read = f => (existsSync(join(dir, f)) ? readFileSync(join(dir, f), 'utf8') : '');

/* ---------- frontmatter（只认 hero / features 这两种结构） ---------- */
function frontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  return m ? m[1] : '';
}
function heroBlock(fm) {
  const lines = fm.split(/\r?\n/);
  const start = lines.findIndex(l => /^hero:\s*$/.test(l));
  if (start < 0) return {};
  const body = [];
  for (let i = start + 1; i < lines.length; i++) {
    if (/^[^\s]/.test(lines[i])) break;      // 回到顶层键就停
    body.push(lines[i]);
  }
  const pick = k => {
    const m = body.map(l => l.match(new RegExp(`^\\s+${k}:\\s*(.+)$`))).find(Boolean);
    return m ? m[1].trim().replace(/^['"]|['"]$/g, '') : '';
  };
  return { name: pick('name'), text: pick('text'), tagline: pick('tagline') };
}
function featureList(fm) {
  const out = [];
  const lines = fm.split(/\r?\n/);
  const start = lines.findIndex(l => /^features:\s*$/.test(l));
  if (start < 0) return out;
  let cur = null;
  for (let i = start + 1; i < lines.length; i++) {
    const line = lines[i];
    if (/^[^\s]/.test(line)) break;                       // 顶层键 → features 结束
    const itemStart = line.match(/^\s{2}-\s+(\w+):\s*(.*)$/);
    if (itemStart) {
      if (cur) out.push(cur);
      cur = { icon: '', title: '', details: '' };
      if (itemStart[1] in cur) cur[itemStart[1]] = itemStart[2].trim();
      continue;
    }
    const kv = line.match(/^\s{4}(\w+):\s*(.*)$/);
    if (kv && cur && kv[1] in cur) cur[kv[1]] = kv[2].trim();
  }
  if (cur) out.push(cur);
  return out
    .filter(f => f.title)
    .map(f => ({
      icon: f.icon.replace(/^['"]|['"]$/g, ''),
      title: f.title.replace(/^['"]|['"]$/g, ''),
      details: f.details.replace(/^['"]|['"]$/g, ''),
    }));
}

/* ---------- 目录：形如 | 01 | [Agent 是什么？](./docs/x.md) | 能学到什么 | ---------- */
function chapters(text) {
  const out = [];
  for (const line of text.split(/\r?\n/)) {
    const cells = line.split('|').map(s => s.trim());
    if (cells.length < 4) continue;
    const no = cells[1], link = cells[2];
    if (!/^\d{1,2}$/.test(no)) continue;
    const title = (link.match(/\[([^\]]+)\]/) || [])[1];
    if (!title) continue;
    out.push({ no, title, hint: cells[3] || '' });
  }
  return out;
}

/* ---------- 组装 ---------- */
const indexMd = read('index.md');
const catalogMd = read('catalog.md');
const readmeMd = read('README.md');
const fm = frontmatter(indexMd);
const hero = heroBlock(fm);
const features = featureList(fm);
const chs = chapters(catalogMd);

/* 仓库名：优先 package.json / git remote 目录名 */
let repo = basename(dir);
if (existsSync(join(dir, 'package.json'))) {
  try { const p = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8')); if (p.name) repo = p.name; } catch {}
}

const content = {
  repo,
  name: hero.name || repo,
  headline: hero.text || '',
  tagline: hero.tagline || '',
  emoji: (hero.name || '').match(/^(\p{Extended_Pictographic})/u)?.[1] || '🧭',
  namePlain: (hero.name || repo).replace(/^\p{Extended_Pictographic}\s*/u, ''),
  chapters: chs.slice(0, 14),
  features: features.slice(0, 6),
  stats: {
    chapters: chs.length,
    features: features.length,
  },
};

writeFileSync(out, JSON.stringify(content, null, 2), 'utf8');
console.log(`content -> ${out}`);
console.log(`  站点: ${content.name}`);
console.log(`  标题: ${content.headline}`);
console.log(`  目录: ${content.chapters.length} 条，特性: ${content.features.length} 条`);
