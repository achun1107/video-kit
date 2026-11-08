# -*- coding: utf-8 -*-
"""仓库结构测试：确认那些「不该提交」的东西真的没提交。

这类测试比单元测试更实际 —— 项目最容易出的事故不是逻辑错，
是把 fonts/ 或者渲染产物 commit 进去了。
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git_files():
    out = subprocess.run(
        ['git', '-c', 'core.quotepath=false', 'ls-files'],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return [f for f in (out.stdout or '').split('\n') if f.strip()]


class TestRepoHygiene:
    def test_no_fonts_committed(self):
        files = git_files()
        bad = [f for f in files if f.startswith('engine/fonts/')]
        assert not bad, f'字体不该入库（43MB）：{bad[:3]}'

    def test_no_renders(self):
        files = git_files()
        bad = [f for f in files if f.startswith(('renders/', 'review/', '_repos/'))]
        assert not bad, f'渲染产物不该入库：{bad[:3]}'

    def test_no_video_files(self):
        files = git_files()
        bad = [f for f in files if f.endswith(('.mp4', '.gif'))]
        assert not bad, f'视频产物不该入库：{bad}'

    def test_audio_only_bgm(self):
        files = git_files()
        audio = [f for f in files if f.startswith('audio/')]
        bad = [f for f in audio if not f.startswith('audio/bgm/')]
        assert not bad, f'audio/ 下只该有 bgm：{bad}'

    def test_no_node_modules(self):
        files = git_files()
        bad = [f for f in files if 'node_modules/' in f]
        assert not bad


class TestRequiredFiles:
    """质检报告要求的门面文件，一个都不能缺。"""

    def test_readme(self):
        assert (ROOT / 'README.md').exists()

    def test_license_is_pure_mit(self):
        """LICENSE 必须是纯 MIT 文本。

        早先把第三方授权说明混进 LICENSE，GitHub 识别成 NOASSERTION，
        点进仓库显示"未知授权"。第三方说明应该在 NOTICE 里。
        """
        txt = (ROOT / 'LICENSE').read_text(encoding='utf-8')
        assert txt.startswith('MIT License')
        assert 'Copyright' in txt
        assert 'Permission is hereby granted' in txt
        # 不该出现第三方素材的字样
        assert 'Kevin MacLeod' not in txt
        assert 'OFL' not in txt
        # 不该有 --- 分隔的第二段
        assert '---' not in txt

    def test_notice_has_third_party(self):
        txt = (ROOT / 'NOTICE').read_text(encoding='utf-8')
        assert 'Kevin MacLeod' in txt
        assert 'OFL' in txt

    def test_agents_md(self):
        p = ROOT / 'AGENTS.md'
        assert p.exists()
        txt = p.read_text(encoding='utf-8')
        # 必须写明那条核心约束
        assert '纯函数' in txt

    def test_llms_txt(self):
        assert (ROOT / 'llms.txt').exists()

    def test_changelog(self):
        p = ROOT / 'CHANGELOG.md'
        assert p.exists()
        assert '1.0.0' in p.read_text(encoding='utf-8')

    def test_security(self):
        assert (ROOT / 'SECURITY.md').exists()

    def test_contributing(self):
        assert (ROOT / 'CONTRIBUTING.md').exists()

    def test_github_dir(self):
        g = ROOT / '.github'
        assert g.is_dir()
        assert (g / 'workflows' / 'ci.yml').exists()
        assert (g / 'copilot-instructions.md').exists()
        assert (g / 'ISSUE_TEMPLATE').is_dir()
        assert (g / 'pull_request_template.md').exists()

    def test_docs(self):
        for f in ['FAQ.md', 'USAGE.md', 'ARCHITECTURE.md']:
            assert (ROOT / 'docs' / f).exists(), f'docs/{f} 缺'

    def test_readme_images_exist(self):
        """README 里引用的本地图片必须真的在仓库里。

        .gitignore 里有一条 /assets/*.png，只顾放行 pipeline.png 时
        social-preview.png 就被挡了，README 引用它会 404。
        """
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        import re
        for m in re.finditer(r'!\[[^\]]*\]\((assets/[^)]+)\)', readme):
            target = ROOT / m.group(1)
            assert target.exists(), f'README 引用了不存在的图：{m.group(1)}'
            tracked = m.group(1) in git_files()
            assert tracked, f'{m.group(1)} 不在 git 里（检查 .gitignore）'


class TestNoSecrets:
    PATTERNS = [
        'ghp_', 'gho_', 'github_pat_', 'sk-', 'AKIA',
        '-----BEGIN', 'xoxb-', 'AIza',
    ]

    def test_no_secret_patterns_in_tracked_files(self):
        """扫当前工作区的所有跟踪文件。

        只报文件名，不打印命中的内容（打印了等于又泄露一次）。
        """
        files = git_files()
        text_ext = ('.md', '.txt', '.py', '.mjs', '.js', '.json', '.yml', '.yaml', '.html')
        # 密钥扫描规则和它的测试文件会被自己的正则命中（里面写着 'ghp_' 字面量），
        # 这两个文件豁免
        SKIP = {'.github/workflows/ci.yml', 'tests/test_repo_structure.py'}
        hits = []
        for f in files:
            if not f.endswith(text_ext) or f in SKIP:
                continue
            p = ROOT / f
            if not p.exists():
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for pat in self.PATTERNS:
                if pat in txt:
                    # 文档里讨论密钥格式是允许的，但要有明显是占位的上下文
                    for line_no, line in enumerate(txt.split('\n'), 1):
                        if pat in line and not any(
                                k in line for k in ('占位', '示例', 'placeholder',
                                                    'your_', 'xxx', '***', '……')):
                            hits.append(f'{f}:{line_no}')
        assert not hits, f'疑似密钥：{hits[:5]}'
