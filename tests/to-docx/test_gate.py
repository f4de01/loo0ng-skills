"""skills/in-progress/to-docx/scripts/gate.py 的脚本层单测（unittest）。

运行：python -m unittest tests/to-docx/test_gate.py

缝是门禁 CLI：给一件 DOCX（正常件由转换器从 fixtures/ 出，故障件在正常件上做 XML 手术），断言 --json 的结论、
不通过项与披露项的项名、退出码、`--deliver` 的落盘行为。

两条跑道（ADR-0017）：默认跑道是**无渲染**，只用门禁本体（静态检查加版面推算），零第三方依赖、任何机器上
都跑得动、不许 skip；末尾几个子类把同一批用例接上渲染层再跑一遍（每件要起一次 Word，约 7 秒），拿不到渲染
通道时整类 skip 并打印一行说明。

断言只断结论类别与项名，不断数值（#59）：要具体数字的地方一律先跑一次无渲染门禁把推算区间读回来，再据它
构造阈值或段数，测试里因此没有一个魔数。
"""
import pathlib
import re
import shutil
import tempfile
import unittest

import support
from support import FIXTURES, W, convert, gate, read_xml, rewrite, template, text_of

RENDER_ONLY_NOTES = ("请求字体不在嵌入字体里", "有字没渲出来（多半是固定行高裁掉了）")


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def item_names(result, key="不通过项"):
    return [x.split("：", 1)[0] for x in result[key]]


class GateCase(unittest.TestCase):
    EXTRA = ("--no-render",)  # 子类置空即接上渲染层

    def setUp(self):
        if not self.EXTRA:
            support.require_render(self)
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-gate-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def gate(self, docx, *extra):
        return gate(docx, *(tuple(self.EXTRA) + extra))

    def build(self, markdown, tpl, name="件.docx"):
        out = self.dir / name
        r = convert(markdown, tpl, out)
        self.assertEqual(r.code, 0, r)
        return out

    def band(self, docx, name):
        """把某项判据的推算区间读回来，供构造阈值用（探针式，取代写死的数值）。"""
        r = support.gate_no_render(docx)
        self.assertIsNotNone(r.result, r)
        return r.result["推算"][name]

    def assert_pass(self, docx, *extra):
        r = self.gate(docx, *extra)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.result["结论"], "通过")
        self.assertEqual(r.result["不通过项"], [])
        self.assertEqual(r.result["需人眼项"], [], "assert_pass 不得接受需人眼这一档（ADR-0017）")
        self.assertEqual(r.result["须目验清单"], "")
        return r

    def assert_fail(self, docx, item, *extra):
        r = self.gate(docx, *extra)
        self.assertEqual(r.code, 1, r)
        self.assertEqual(r.result["结论"], "不通过")
        self.assertIn(item, item_names(r.result), r.result)
        return r

    def assert_needs_eye(self, docx, item, *extra):
        r = self.gate(docx, *extra)
        self.assertEqual(r.code, 3, r)
        self.assertEqual(r.result["结论"], "需人眼")
        self.assertEqual(r.result["不通过项"], [])
        self.assertIn(item, item_names(r.result, "需人眼项"), r.result)
        return r


class NormalAndFaultPairs(GateCase):
    """五种故障样例各一件必拦，正常件必过；收尾两条规则各一对。"""

    def test_normal_passes_with_disclosures(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        r = self.assert_pass(docx, "--template", template("1-2."))
        notes = r.result["披露项"]
        names = item_names(r.result, "披露项")
        self.assertIn("空单元格：第 1 张表 第 2 行第 2 格", notes, "印模格本来就空，只披露")
        self.assertIn("页数", names)
        if r.result["渲染"] is None:
            self.assertIn("无渲染结果", names)
            for name in RENDER_ONLY_NOTES:
                self.assertNotIn(name, names, "无渲染时渲染侧披露项整条消失，不报「无」")
        else:
            self.assertIn("请求字体不在嵌入字体里", names)
            self.assertNotIn("无渲染结果", names)

    def test_long_marker_stretches_a_row(self):
        docx = self.build(fixture("撑列.md"), template("1-2."))
        r = self.assert_fail(docx, "行高超阈值")
        self.assertIn("磅", r.result["不通过项"][0])

    def test_blank_page(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))
        n, bad = self.probe_blank_page(good)
        r = self.assert_fail(bad, "空白页")
        self.assertIn("第", r.result["不通过项"][0], "空白页项要带坐标：%d 个空段" % n)

    def probe_blank_page(self, good):
        """探针：往正文尾部塞空段，直到推算的上下界都说末页是空白页（不写死段数）。"""
        def make(n):
            def pad(data):
                xml = data.decode("utf-8")
                return xml.replace("<w:sectPr", "<w:p/>" * n + "<w:sectPr", 1).encode("utf-8")
            return rewrite(good, self.dir / ("空白页-%d.docx" % n), {"word/document.xml": pad})

        n = 8
        while n <= 512:
            bad = make(n)
            r = support.gate_no_render(bad)
            if "空白页" in item_names(r.result):
                return n, bad
            n *= 2
        raise AssertionError("塞到 512 个空段都推算不出必然的空白页")

    def test_metadata_leftover(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))

        def leak(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<dc:creator/>|<dc:creator></dc:creator>", "<dc:creator>某人</dc:creator>", xml)
            xml = xml.replace("</cp:coreProperties>", "<cp:lastPrinted>2022-09-08T06:43:00Z</cp:lastPrinted></cp:coreProperties>")
            return xml.encode("utf-8")

        bad = rewrite(good, self.dir / "元数据.docx", {"docProps/core.xml": leak})
        r = self.assert_fail(bad, "元数据残留")
        self.assertIn("作者", r.result["不通过项"][0])
        self.assertIn("上次打印时间", r.result["不通过项"][0])

    def test_table_directly_before_sectpr(self):
        good = self.build("# 题\n\n| 印章名称 | 甲 |\n|---|---|\n", template("1-2."), "表尾.docx")
        self.assert_pass(good)

        def drop_trailing_paragraph(data):
            xml = data.decode("utf-8")
            return re.sub(r"<w:p>(?:(?!<w:p>).)*?</w:p>(?=<w:sectPr)", "", xml, count=1, flags=re.S).encode("utf-8")

        bad = rewrite(good, self.dir / "表接sectPr.docx", {"word/document.xml": drop_trailing_paragraph})
        blocks = support.body_blocks(bad)
        self.assertEqual(blocks[-1].tag, W + "tbl", "手术后最后一块须是表")
        self.assert_fail(bad, "表格直接接 sectPr")

    def test_table_wider_than_the_page(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))

        def widen(data):
            xml = data.decode("utf-8")
            return re.sub(r'<w:gridCol w:w="\d+"/>', '<w:gridCol w:w="6000"/>', xml).encode("utf-8")

        bad = rewrite(good, self.dir / "表宽.docx", {"word/document.xml": widen})
        self.assert_fail(bad, "表宽超页面")

    def test_template_table_dropped_needs_template(self):
        """模板有表而成品没表即不通过（#107）。

        真事故：模型为了过「行高超阈值」，把模板规定的那张表整个改写成正文段落，
        几何违规随表一起消失、门禁给通过，交出去的是一份缺了正文结构的件。
        钉子只在稿子里有表时才落进成品，所以这一项必须由门禁自己拦，不能指望种子。
        """
        tpl = template("1-2.")
        表 = fixture("印章备案.md")
        管道表 = "\n".join([
            "| 印章名称 | 乙公司管理人章、乙公司管理人财务专用章 |",
            "|---|---|",
            "| 印模 |  |",
            "| 启用时间 | 甲年乙月丙日 |",
        ])
        段落 = "\n\n".join([
            "印章名称：乙公司管理人章、乙公司管理人财务专用章",
            "印模：",
            "启用时间：甲年乙月丙日",
        ])
        self.assertIn(管道表, 表, "fixture 里那张管道表的写法变了，改这里")
        无表 = 表.replace(管道表, 段落)

        good = self.build(表, tpl, "有表.docx")
        self.assert_pass(good, "--template", tpl)

        bad = self.build(无表, tpl, "无表.docx")
        self.assert_fail(bad, "模板表缺失", "--template", tpl)
        r = self.gate(bad)
        self.assertEqual(r.code, 0, "没有模板可比时，成品没表不算错")
        self.assertIn("未给 --template", item_names(r.result, "披露项"))

    def test_placeholder_leftover(self):
        docx = self.build(fixture("占位残留.md"), template("1-2."))
        r = self.assert_fail(docx, "模板占位残留")
        line = r.result["不通过项"][0]
        self.assertIn("XX", line)
        self.assertIn("【印模待补】", line)

    def test_template_note_paragraph_leftover_needs_template(self):
        tpl = template("4-2.")
        note = text_of(read_xml(tpl).find(W + "body").find(W + "p")).strip()
        self.assertTrue(note.startswith("（注"), note)
        md = "# 关于提请法院裁定宣告乙公司破产并终结破产程序的报告\n\n" + note + "\n\n:left: 甲法院：\n\n正文一段。\n"
        docx = self.build(md, tpl)
        self.assert_fail(docx, "模板原文残留", "--template", tpl)
        r = self.gate(docx)
        self.assertEqual(r.code, 0, "不给模板就查不到说明段残留，只披露没比对")
        self.assertIn("未给 --template", item_names(r.result, "披露项"))

    def test_page_field_hardcoded_and_missing(self):
        tpl = template("3-1.")
        good = self.build(fixture("债权确认.md"), tpl, "债权.docx")
        self.assert_pass(good, "--template", tpl)

        def hardcode(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<w:instrText[^>]*>[^<]*</w:instrText>", "<w:instrText xml:space=\"preserve\"> DUMMY </w:instrText>", xml)
            return xml.encode("utf-8")

        bad = rewrite(good, self.dir / "写死.docx", {"word/footer1.xml": hardcode})
        self.assert_fail(bad, "页脚 PAGE 域写死")

        def remove_all_text(data):
            xml = data.decode("utf-8")
            xml = re.sub(r"<w:instrText[^>]*>[^<]*</w:instrText>", "", xml)
            xml = re.sub(r"<w:t(?: [^>]*)?>[^<]*</w:t>", "", xml)
            return xml.encode("utf-8")

        gone = rewrite(good, self.dir / "丢失.docx", {"word/footer1.xml": remove_all_text})
        self.assert_fail(gone, "页脚 PAGE 域丢失", "--template", tpl)
        r = self.gate(gone)
        self.assertEqual(r.code, 0, "没有模板可比时，页脚没字不算错")

    def test_page_count_threshold(self):
        docx = self.multi_page_docx()
        lo, _ = self.band(docx, "页数")
        self.assertGreater(lo, 1, "探针件的推算下界须多于一页")
        self.assert_fail(docx, "页数超阈值", "--max-pages", str(lo - 1))
        self.assert_pass(docx)

    def multi_page_docx(self):
        """探针：正文段数翻倍到推算下界都超过一页为止（不写死段数）。"""
        n = 8
        while n <= 512:
            md = "# 题\n\n" + "".join("第 %d 段，甲乙丙丁戊己庚辛壬癸，甲乙丙丁戊己庚辛壬癸。\n\n" % i for i in range(1, n))
            docx = self.build(md, template("1-2."), "多页-%d.docx" % n)
            if support.gate_no_render(docx).result["推算"]["页数"][0] > 1:
                return docx
            n *= 2
        raise AssertionError("写到 512 段都推算不出第二页")

    def test_row_height_threshold_is_adjustable(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lo, _ = self.band(docx, "最大行高")
        self.assert_fail(docx, "行高超阈值", "--max-row-height", "%.1f" % (lo / 2))
        self.assert_pass(docx)


class ThreeValuedConclusion(GateCase):
    """需人眼这一档：阈值落在推算区间内，门禁测不准而非测出事故（ADR-0017）。

    这几件恒走无渲染跑道：区间存在的唯一原因就是这台机器上没有渲染器，渲染层一在场这一档当场坍缩。
    """

    def test_threshold_inside_the_band_is_needs_eye_and_still_delivers(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lo, hi = self.band(docx, "最大行高")
        self.assertLess(lo, hi, "推算给的是区间不是点值")
        target = self.dir / "文书" / "印章备案" / "印章备案-v1.docx"
        r = self.assert_needs_eye(docx, "最大行高测不准", "--max-row-height", "%.1f" % lo, "--deliver", target)
        self.assertEqual(r.result["已落盘"], str(target), "需人眼件照常落盘，位置与通过件相同")
        self.assertEqual(target.name, "印章备案-v1.docx", "文件名不加任何装饰")
        self.assertEqual(target.read_bytes(), docx.read_bytes())

    def test_the_regression_fixtures_are_in_the_band_at_the_default_thresholds(self):
        """带内这一档不是靠喂一个凑出来的阈值：这两件在**默认阈值**上就落在带内。

        它们的真值 Word 与 WPS 各量过一列（冻在 `test_layout_estimate.py` 的 FROZEN 里）：行高件两个引擎
        都是 200.5 磅、默认阈值 200 磅；页数件两个引擎都是 30 页、默认阈值 30 页。推算分不出它们在阈值
        哪一侧，正是这一档存在的理由。
        """
        cases = (("推算-行高贴阈值.md", "最大行高测不准", "最大行高"),
                 ("推算-页数贴阈值.md", "页数测不准", "页数"))
        for name, item, 项名 in cases:
            with self.subTest(件=name):
                stem = name.replace(".md", "")
                docx = self.build(fixture(name), template("1-2."), stem + ".docx")
                target = self.dir / "文书" / stem / (stem + "-v1.docx")
                r = self.assert_needs_eye(docx, item, "--deliver", target)
                self.assertEqual(r.result["已落盘"], str(target), "需人眼件照常落盘")
                self.assertEqual(target.read_bytes(), docx.read_bytes())
                self.assertIn("- %s：" % 项名, r.result["须目验清单"])

    def test_assert_pass_never_accepts_the_third_grade(self):
        """结论值域每多一档，fixture 必多一件把那一档钉住，且 assert_pass 不得接受该档（ADR-0017）。"""
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lo, _ = self.band(docx, "最大行高")
        with self.assertRaises(AssertionError):
            self.assert_pass(docx, "--max-row-height", "%.1f" % lo)

    def test_needs_eye_report_starts_with_the_checklist(self):
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lo, hi = self.band(docx, "最大行高")
        r = self.assert_needs_eye(docx, "最大行高测不准", "--max-row-height", "%.1f" % lo)
        block = r.result["须目验清单"]
        lines = block.splitlines()
        self.assertEqual(lines[0], "须目验清单")
        self.assertEqual(lines[-1], "确认前请在 WPS 或 Word 里打开看这几处。")
        self.assertTrue(lines[1].startswith("- 最大行高："), lines)
        for piece in ("张表第", "推算", "阈值", "最坏越界"):
            self.assertIn(piece, lines[1], "每行要带项名、坐标、推算区间与最坏越界幅度")
        plain = support.run(support.GATE, docx, "--no-render", "--max-row-height", "%.1f" % lo)
        self.assertTrue(plain.out.startswith("须目验清单\n"), "清单是审查报告的第一段")

    def test_a_fail_outranks_a_needs_eye_and_nothing_is_delivered(self):
        """同件兼有两档时结论取不通过，重试针对不通过项；不通过件一个字不改、永不落盘。"""
        docx = self.build(fixture("占位残留.md"), template("1-2."))
        lo, _ = self.band(docx, "最大行高")
        target = self.dir / "文书" / "件-v1.docx"
        r = self.assert_fail(docx, "模板占位残留", "--max-row-height", "%.1f" % lo, "--deliver", target)
        self.assertTrue(r.result["需人眼项"], "两档同时在，结论取重的那档")
        self.assertEqual(r.result["须目验清单"], "", "不通过件不落盘，也就没有那份审查报告")
        self.assertFalse(target.exists())


class DeliverAndBackend(GateCase):
    def test_deliver_only_on_pass_and_never_overwrites(self):
        good = self.build(fixture("印章备案.md"), template("1-2."))
        target = self.dir / "文书" / "印章备案" / "印章备案-v1.docx"
        r = self.gate(good, "--deliver", target)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.result["已落盘"], str(target))
        self.assertEqual(target.read_bytes(), good.read_bytes())
        r2 = self.gate(good, "--deliver", target)
        self.assertEqual(r2.code, 2, "落盘被拒不是「文书不合格」，从 1 挪到 2（ADR-0017）")
        self.assertEqual(r2.result["结论"], "通过")
        self.assertIn("不覆盖", r2.result["落盘被拒"])
        self.assertIn("落盘被拒", r2.err)
        self.assertEqual(target.read_bytes(), good.read_bytes())

    def test_fail_means_nothing_is_delivered(self):
        bad = self.build(fixture("占位残留.md"), template("1-2."))
        target = self.dir / "文书" / "件-v1.docx"
        r = self.gate(bad, "--deliver", target)
        self.assertEqual(r.code, 1)
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists(), "不通过连目录都不建")

    def test_lawyer_written_docx_is_checked_the_same_way(self):
        r = self.gate(template("1-2."))
        self.assertEqual(r.code, 1, "官方模板原件带作者与占位符，照样报出")
        self.assertIn("元数据残留", support.strip_ws(r.out))
        self.assertTrue(r.result["披露项"], "披露项照给，供审查报告只披露不阻断")

    def test_missing_render_backend_still_concludes(self):
        """无渲染后端是主力环境的正常路径，这条跑道必须给出结论（#59 第 9 条，本票反向重写）。"""
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lanes = [("--powershell", self.dir / "没有这个.exe")]
        fake = self.dir / "fakeps.bat"
        fake.write_text("@echo NOWORD fake\r\n@exit /b 3\r\n", encoding="ascii")
        lanes.append(("--powershell", fake))
        lanes.append(("--no-render",))
        for lane in lanes:
            with self.subTest(lane=lane[-1]):
                r = gate(docx, *lane)
                self.assertEqual(r.code, 0, r)
                self.assertEqual(r.result["结论"], "通过")
                self.assertIsNone(r.result["渲染"])
                self.assertIn("无渲染结果", item_names(r.result, "披露项"))
                for name in RENDER_ONLY_NOTES:
                    self.assertNotIn(name, item_names(r.result, "披露项"))

    def test_broken_docx_is_exit_2(self):
        broken = self.dir / "坏.docx"
        broken.write_bytes(b"not a zip")
        r = support.run(support.GATE, broken)
        self.assertEqual(r.code, 2)
        r = support.run(support.GATE, self.dir / "没有.docx")
        self.assertEqual(r.code, 2)
        r = support.run(support.GATE, self.build(fixture("印章备案.md"), template("1-2.")),
                        "--template", self.dir / "没有模板.docx")
        self.assertEqual(r.code, 2)


class NormalAndFaultPairsRendered(NormalAndFaultPairs):
    """同一批用例接上渲染层再跑一遍：点值取代区间。缺渲染通道时整类 skip 并打印说明（ADR-0017）。"""
    EXTRA = ()

    def test_render_point_inside_the_estimated_band(self):
        """渲染点值落在推算区间外要出固定名披露项；本机的正常件不该触发它。"""
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        r = self.assert_pass(docx)
        self.assertEqual(r.result["推算区间不含实测值"], [], r.result)
        lo, hi = r.result["推算"]["最大行高"]
        self.assertLessEqual(lo, r.result["渲染"]["最大行高"])
        self.assertLessEqual(r.result["渲染"]["最大行高"], hi)

    def test_render_collapses_the_third_grade(self):
        """渲染层在场时需人眼当场坍缩：同一个带内阈值在这条跑道上只会给出二值。"""
        docx = self.build(fixture("印章备案.md"), template("1-2."))
        lo, hi = self.band(docx, "最大行高")
        r = self.gate(docx, "--max-row-height", "%.1f" % lo)
        self.assertIn(r.result["结论"], ("通过", "不通过"))
        self.assertEqual(r.result["需人眼项"], [])


if __name__ == "__main__":
    unittest.main()
