"""版面推算层（门禁本体）的回归：三件推算回归件 + 构造属性两条。

运行：python -m unittest tests/to-docx/test_layout_estimate.py

这一整个文件**不起渲染器**，在任何机器上都必须全绿、不许 skip（ADR-0017 改了 ADR-0015 的口径：门禁本体
是零第三方依赖的推算层，永远在）。

三件回归件钉的是 #55 自报的三条空白，不是门禁结论：
  1. 贴阈值行高（样本里 114–120 与 397–509 之间是空的，这件落在 200 磅一带）
  2. 页数打默认的 30 页阈值必落带内的长件
  3. 空白页在页边界收尾的件（同一份正文配两个空段数，真值一件有空白页一件没有）

真值是**造件时** Word 与 WPS 各量一次冻在下面的常量里的，之后测试零依赖、永不重量：渲染器是造 fixture
的工具，不是跑 fixture 的前提（#59 第 8 条）。断言只断「推算区间包住真值」，不断推算自己算出的数。

冻的是 `fixtures/` 里那三份 **docx** 本身。它们本是 Markdown 稿由那时的转换器出来的，#13 起那条路整个
退场，稿子与出稿的脚本都没了，而**被量过的就是这几份字节**：把产物留下来，真值与件才仍然对得上；空段
那一次 XML 手术照旧在跑测试时做。
"""
import builtins
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

import support
from support import FIXTURES

sys.path.insert(0, str(support.SCRIPTS))
import gate  # noqa: E402  门禁本体零第三方依赖，import 得动本身就是 A.1 的一次实跑

# 造件时量的两列真值（本机 Word 16.0 与 WPS 12.1，逐件两列相同）。改动件的内容就必须重量。
FROZEN = (
    {
        "件": "推算-行高贴阈值.docx", "空段": 0,
        "钉的空白": "最大行高落在 120～400 磅这一段（#55 的样本里没有件）",
        "真值": {"Word": {"页数": 1, "空白页": [], "最大行高": 200.5},
               "WPS": {"页数": 1, "空白页": [], "最大行高": 200.5}},
    },
    {
        "件": "推算-页数贴阈值.docx", "空段": 0,
        "钉的空白": "页数正打默认的 30 页阈值，必落带内",
        "真值": {"Word": {"页数": 30, "空白页": [], "最大行高": 0.0},
               "WPS": {"页数": 30, "空白页": [], "最大行高": 0.0}},
    },
    {
        "件": "推算-空白页页边界.docx", "空段": 18,
        "钉的空白": "空白页在页边界收尾：这一个空段数下末页没有溢出",
        "真值": {"Word": {"页数": 2, "空白页": [], "最大行高": 0.0},
               "WPS": {"页数": 2, "空白页": [], "最大行高": 0.0}},
    },
    {
        "件": "推算-空白页页边界.docx", "空段": 36,
        "钉的空白": "同一份正文再多塞些空段，末页溢出成空白页",
        "真值": {"Word": {"页数": 3, "空白页": [3], "最大行高": 0.0},
               "WPS": {"页数": 3, "空白页": [3], "最大行高": 0.0}},
    },
)


class LayoutEstimateCase(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-estimate-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def build(self, case):
        """冻结的那一份 docx，再按冻结的空段数做一次 XML 手术。"""
        src = FIXTURES / case["件"]
        self.assertTrue(src.is_file(), "冻结的回归件不在了：%s" % src)
        if not case["空段"]:
            return src

        def pad(data, n=case["空段"]):
            return data.decode("utf-8").replace("<w:sectPr", "<w:p/>" * n + "<w:sectPr", 1).encode("utf-8")

        return support.rewrite(src, self.dir / ("%s-%d-空段.docx" % (src.stem, case["空段"])),
                               {"word/document.xml": pad})

    def bands(self, docx):
        return gate.estimate_ranges(gate.Docx(docx))


class EstimateCoversTheMeasuredTruth(LayoutEstimateCase):
    def test_every_frozen_truth_falls_inside_the_estimated_band(self):
        for case in FROZEN:
            docx = self.build(case)
            band = self.bands(docx)
            for engine, truth in case["真值"].items():
                with self.subTest(件=case["件"], 空段=case["空段"], 引擎=engine):
                    lo, hi = band["页数"]
                    self.assertLessEqual(lo, truth["页数"], case["钉的空白"])
                    self.assertLessEqual(truth["页数"], hi, case["钉的空白"])
                    lo, hi = band["最大行高"]
                    self.assertLessEqual(lo, truth["最大行高"], case["钉的空白"])
                    self.assertLessEqual(truth["最大行高"], hi, case["钉的空白"])
                    lo, hi = band["空白页"]
                    self.assertLessEqual(lo, len(truth["空白页"]))
                    self.assertLessEqual(len(truth["空白页"]), hi)
                    for page in truth["空白页"]:
                        self.assertIn(page, band["空白页坐标"], "真的空白页要在推算点到的那几页里")

    def test_the_two_engines_agree_on_every_frozen_truth(self):
        """两列真值逐件相同（#60 的结论），所以「区间同时包住两个」这条断言不是自欺。"""
        for case in FROZEN:
            with self.subTest(件=case["件"], 空段=case["空段"]):
                self.assertEqual(case["真值"]["Word"], case["真值"]["WPS"])

    def test_the_three_fixtures_still_sit_in_the_blind_spots_they_were_built_for(self):
        by_name = {}
        for case in FROZEN:
            by_name.setdefault(case["件"], []).append(case)

        tall = by_name["推算-行高贴阈值.docx"][0]["真值"]["Word"]["最大行高"]
        self.assertLess(120.0, tall, "行高件要落在 #55 自报的 120～400 磅空白里")
        self.assertLess(tall, 400.0)

        pages = by_name["推算-页数贴阈值.docx"][0]["真值"]["Word"]["页数"]
        self.assertLessEqual(abs(pages - gate.DEFAULT_MAX_PAGES), 1, "页数件要贴着默认阈值")

        blanks = [len(c["真值"]["Word"]["空白页"]) for c in by_name["推算-空白页页边界.docx"]]
        self.assertEqual(sorted(blanks), [0, 1], "空白页那一对要一件有一件没有")

    def test_the_blank_page_pair_is_exactly_what_the_third_grade_is_for(self):
        """同一区间、相反真值：推算分不出这一对，这正是需人眼这一档存在的理由。"""
        bands = []
        for case in [c for c in FROZEN if c["件"] == "推算-空白页页边界.docx"]:
            bands.append(self.bands(self.build(case))["空白页"])
        self.assertEqual(bands[0], bands[1], "两件的空白页区间相同")
        lo, hi = bands[0]
        self.assertEqual(gate._verdict(lo, hi, 0.0), "需人眼", "阈值 0 落在区间内即需人眼")


class EstimateIsConstructedNotMeasured(LayoutEstimateCase):
    """取代「跨环境一致」那条验收（不押在拿不到的 Mac 上）：钉推算器的构造属性（#59 第 5 条）。"""

    def test_estimating_opens_no_file_at_all_let_alone_a_font_file(self):
        """断言比「不打开字体文件」更强：一个文件都不打开，字体文件因此无从谈起。

        盯 `builtins.open` 与 `os.open` 两处：`zipfile` 与 `io.open` 最终都落到前者，后者是绕过它的那条路。
        """
        docx = self.build(FROZEN[0])
        doc = gate.Docx(docx)  # 打开 DOCX 这一次在推算之外
        opened = []
        real = {"open": builtins.open, "os_open": os.open}

        def spy_open(file, *a, **kw):
            opened.append(str(file))
            return real["open"](file, *a, **kw)

        def spy_os_open(path, *a, **kw):
            opened.append(str(path))
            return real["os_open"](path, *a, **kw)

        builtins.open, os.open = spy_open, spy_os_open
        try:
            band = gate.estimate_ranges(doc)
        finally:
            builtins.open, os.open = real["open"], real["os_open"]
        self.assertTrue(band)
        self.assertEqual(opened, [], "推算全程一个文件都不打开（因此不受字体替换影响）：%s" % opened)

    def test_the_same_docx_estimates_to_the_same_numbers(self):
        docx = self.build(FROZEN[1])
        first = self.bands(docx)
        self.assertEqual(first, self.bands(docx), "同一件在同一进程里推算两遍结果相同")
        out = [support.gate_no_render(docx).result["推算"] for _ in range(2)]
        self.assertEqual(out[0], out[1], "另起进程再推算两遍，结果仍相同")

    def test_the_estimator_needs_no_third_party_module(self):
        self.assertNotIn("pymupdf", sys.modules, "光跑推算层不该把 PyMuPDF 拉进来")


if __name__ == "__main__":
    unittest.main()
