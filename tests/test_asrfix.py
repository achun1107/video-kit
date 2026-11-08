# -*- coding: utf-8 -*-
"""asrfix.py 的测试。

这些用例全部来自实际踩过的坑，不是编的：
  · HyperFrames 被 whisper 听成 "Happy Frames"
  · 循环 replace 会把替换结果再吃一次，叠出 "HyperFramess"
  · "紫围斗树" 是 "紫微斗数" 的近音误听
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))

from asrfix import clean_keywords, fix_text


class TestFixText:
    def test_gatehub_becomes_github(self):
        # 注意 "狂懒" 也在纠正表里（→ 斩获），所以断言要连它一起算上
        assert fix_text('在Gatehub狂懒1万star') == '在GitHub斩获1万star'

    def test_ziwei_doushu(self):
        assert fix_text('紫围斗树这个项目') == '紫微斗数这个项目'

    def test_codes_becomes_codex(self):
        assert fix_text('给CodeS配上') == '给Codex配上'

    def test_wenruan_becomes_microsoft(self):
        assert fix_text('温软开源') == '微软开源'

    def test_happy_frames_becomes_hyperframes(self):
        assert fix_text('第一个Happy Frames') == '第一个HyperFrames'

    def test_no_double_replacement(self):
        """循环 replace 会把 HyperFrames 里的 HyperFrame 再吃一次 → HyperFramess。

        必须一次性替换（所有 key 合成正则 alternation）。
        """
        out = fix_text('Happy Frames')
        assert out == 'HyperFrames'
        assert 'HyperFramess' not in out
        assert out.count('HyperFrames') == 1

    def test_idempotent(self):
        """纠正过的文本再纠正一遍不该变。"""
        once = fix_text('紫围斗树在Gatehub')
        twice = fix_text(once)
        assert once == twice

    def test_empty(self):
        assert fix_text('') == ''
        assert fix_text(None) is None

    def test_multiple_in_one_sentence(self):
        s = '温软在Gatehub上，紫围斗树这个项目给CodeS用'
        out = fix_text(s)
        assert '微软' in out
        assert 'GitHub' in out
        assert '紫微斗数' in out
        assert 'Codex' in out

    def test_english_case_insensitive(self):
        assert 'GitHub' in fix_text('GATEHUB')
        assert 'HyperFrames' in fix_text('happy frames')


class TestCleanKeywords:
    def test_removes_stopwords(self):
        """虚词和高频词要被滤掉，专名要留下。"""
        kws = clean_keywords(['这个', '项目', '紫微斗数', '开源'])
        assert '紫微斗数' in kws
        assert '这个' not in kws
        assert '项目' not in kws
        assert '开源' not in kws

    def test_drops_single_chars(self):
        kws = clean_keywords(['紫', '微', '紫微斗数'])
        assert '紫' not in kws
        assert '微' not in kws
        assert '紫微斗数' in kws

    def test_strips_punctuation(self):
        kws = clean_keywords(['，紫微斗数。'])
        assert any('紫微斗数' in k for k in kws)

    def test_empty_input(self):
        assert clean_keywords([]) == []
