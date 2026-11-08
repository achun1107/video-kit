# -*- coding: utf-8 -*-
"""repo-finder.py 里纯函数的测试。

重点测两处最容易出错的：
  · parse_cn_number —— 中文数字解析（"一点八万" = 18000，"3.6万" = 36000）
  · find_star_hint —— 只认跟着 star/星 的数字，不能把"67.5万张命盘"当成 star 数
"""
import sys
import importlib.util
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOLS))

# tools/repo-finder.py 文件名带连字符，不能直接 import，得用 importlib 加载
_spec = importlib.util.spec_from_file_location('repo_finder', TOOLS / 'repo-finder.py')
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_cn_number = _mod.parse_cn_number
find_star_hint = _mod.find_star_hint
find_org = _mod.find_org


class TestParseCnNumber:
    def test_plain_digits(self):
        assert parse_cn_number('3.6') == 3.6
        assert parse_cn_number('1.05') == 1.05
        assert parse_cn_number('42') == 42

    def test_cn_decimal(self):
        assert parse_cn_number('一点八') == 1.8
        assert parse_cn_number('三点六') == 3.6

    def test_arabic_with_cn_dot(self):
        assert parse_cn_number('3点6') == 3.6

    def test_simple_cn(self):
        assert parse_cn_number('十八') == 18
        assert parse_cn_number('三') == 3

    def test_cn_ten_thousand(self):
        assert parse_cn_number('三万六') == 36000
        assert parse_cn_number('一万') == 10000

    def test_invalid(self):
        assert parse_cn_number('') is None
        assert parse_cn_number('abc') is None


class TestFindStarHint:
    def test_basic(self):
        hints = find_star_hint('在GitHub斩获1.05万star')
        assert len(hints) == 1
        assert hints[0][0] == 10500

    def test_cn_number(self):
        hints = find_star_hint('一点八万star')
        assert hints and hints[0][0] == 18000

    def test_with_line_break_variant(self):
        """whisper 把 star 听成 "行标"。"""
        hints = find_star_hint('3.6万行标')
        assert hints and hints[0][0] == 36000

    def test_ignores_number_without_star_keyword(self):
        """这是关键的回归测试。

        "67.5万张命盘" 不是 star 数。早先版本会把它也当成 star 线索，
        结果 44 万 star 的无关仓库匹配度反而最高（441068/675000=0.65 落在区间里）。
        """
        hints = find_star_hint('一共67.5万张命盘，877万段解读')
        assert hints == []

    def test_multiple(self):
        hints = find_star_hint('先是1.05万star，后来涨到2万star')
        values = [h[0] for h in hints]
        assert 10500 in values
        assert 20000 in values

    def test_dedup(self):
        hints = find_star_hint('1.05万star 还有 1.05万star')
        assert len(hints) == 1

    def test_small_numbers_ignored(self):
        """小于 100 的不算（"5颗星" 这种不是 star 数）。"""
        assert find_star_hint('评分5星') == []


class TestFindOrg:
    def test_bytedance(self):
        assert find_org('字节开源黑科技') == 'bytedance'

    def test_bytedance_alt(self):
        assert find_org('字节跳动') == 'bytedance'

    def test_microsoft(self):
        assert find_org('微软开源') == 'microsoft'

    def test_microsoft_misheard(self):
        """whisper 把"微软"听成"温软"。"""
        assert find_org('温软将把这个做成了框架') == 'microsoft'

    def test_alibaba(self):
        assert find_org('阿里巴巴') == 'alibaba'

    def test_none(self):
        assert find_org('一个普通的开源项目') is None

    def test_empty(self):
        assert find_org('') is None
