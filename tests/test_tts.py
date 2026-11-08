# -*- coding: utf-8 -*-
"""tts.py 的 SRT 解析测试。

SRT 时间是字幕的唯一来源 —— 解析错了，字幕就会和配音对不上。
edge-tts 输出的 SRT 有重叠（上一条的结束时间晚于下一条的开始），
这是正常的，只要顺序和时间点对就行。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))

from tts import parse_srt, srt_time


class TestSrtTime:
    def test_basic(self):
        assert srt_time('00:00:00,100') == 0.1
        assert srt_time('00:00:01,325') == 1.325

    def test_minutes(self):
        assert srt_time('00:01:30,500') == 90.5

    def test_hours(self):
        assert srt_time('01:00:00,000') == 3600.0

    def test_invalid(self):
        assert srt_time('garbage') == 0.0
        assert srt_time('') == 0.0


class TestParseSrt:
    def test_single_block(self, tmp_path):
        p = tmp_path / 'a.srt'
        p.write_text(
            '1\n00:00:00,100 --> 00:00:01,325\n默认配色看腻了？\n',
            encoding='utf-8')
        segs = parse_srt(str(p))
        assert len(segs) == 1
        a, b, txt = segs[0]
        assert abs(a - 0.1) < 1e-6
        assert abs(b - 1.325) < 1e-6
        assert txt == '默认配色看腻了？'

    def test_multiple_blocks(self, tmp_path):
        p = tmp_path / 'b.srt'
        p.write_text(
            '1\n00:00:00,100 --> 00:00:01,325\n第一句\n\n'
            '2\n00:00:01,275 --> 00:00:03,586\n第二句\n\n'
            '3\n00:00:03,586 --> 00:00:08,293\n第三句\n',
            encoding='utf-8')
        segs = parse_srt(str(p))
        assert len(segs) == 3
        assert [s[2] for s in segs] == ['第一句', '第二句', '第三句']

    def test_overlapping_times_allowed(self, tmp_path):
        """edge-tts 的输出里上一句结束晚于下一句开始，这是正常的。"""
        p = tmp_path / 'c.srt'
        p.write_text(
            '1\n00:00:00,100 --> 00:00:01,325\nA\n\n'
            '2\n00:00:01,275 --> 00:00:03,586\nB\n',
            encoding='utf-8')
        segs = parse_srt(str(p))
        assert segs[0][1] > segs[1][0]      # 结束 1.325 > 下一个开始 1.275

    def test_multiline_text(self, tmp_path):
        p = tmp_path / 'd.srt'
        p.write_text(
            '1\n00:00:00,100 --> 00:00:02,000\n上半句\n下半句\n',
            encoding='utf-8')
        segs = parse_srt(str(p))
        assert len(segs) == 1
        assert segs[0][2] == '上半句下半句'

    def test_empty_file(self, tmp_path):
        p = tmp_path / 'e.srt'
        p.write_text('', encoding='utf-8')
        assert parse_srt(str(p)) == []
