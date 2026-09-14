"""skills/in-progress/to-docx/scripts/gate.py 的脚本层单测（unittest）。

运行：python -m unittest tests/to-docx/test_gate.py

缝是门禁 CLI：给一件 DOCX（正常件由 fill.py 拿官方模板填出来，故障件在正常件上做 XML 手术），断言 --json 的
结论、不通过项与披露项的项名、退出码、`--deliver` 的落盘行为。

门禁缩成两样之后（ADR-0023，#13）：第一样是**改动段**没有残留占位且不在高亮里（`--changed` 给段号，不给
就不查、只出一条披露项；律师改过的位置不在那串里，因此不受检），第二样是几何不超阈值（推算层原样保留）。
全篇查占位与模板说明段整段残留两条随差量路线删掉：缺的槽保留原占位加黄正是出件的正常形态。

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
import zipfile

import support
from support import W, apply, fill_all_ops, gate, read_xml, rewrite, template, 填

RENDER_ONLY_NOTES = ("请求字体不在嵌入字体里", "有字没渲出来（多半是固定行高裁掉了）")


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

    def build(self, tpl=None, ops=None, name="件.docx", *extra):
        """正常件：拿官方模板当载体填一遍。不给 ops 就全填（一处黄都不剩，最接近一份出好的件）。"""
        tpl = tpl or template("1-2.")
        out = self.dir / name
        r = apply(tpl, fill_all_ops(tpl) if ops is None else ops, out, *extra)
        self.assertEqual(r.code, 0, r)
        self.last_changed = r.changed        # 上一件的改动段号，交给 --changed
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

    def 半填不留黄(self, name="半填.docx"):
        """只填一个槽、不留黄：那一段还剩十来个占位，正是门禁第一样要拦的样子。"""
        return self.build(None, [{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], name, "--no-highlight-rest")


class ChangedParagraphs(GateCase):
    """门禁第一样：改动段没有残留占位且不在高亮里。"""

    def test_a_changed_paragraph_with_a_bare_placeholder_fails(self):
        docx = self.半填不留黄()
        r = self.assert_fail(docx, "改动段残留占位", "--changed", "2")
        self.assertIn("p2", r.result["不通过项"][0])

    def test_the_same_change_passes_once_the_rest_is_highlighted(self):
        """代码统一留黄之后同一件就该过：缺的槽留原占位加黄是出件的正常形态（ADR-0023）。"""
        docx = self.build(None, [{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], "留黄.docx")
        self.assert_pass(docx, "--changed", ",".join(str(i) for i in self.last_changed))

    def test_placeholders_outside_the_changed_paragraphs_are_nobodys_business(self):
        """律师改过的位置不在 --changed 里，因此不受检；模板自带的槽同理。"""
        docx = self.半填不留黄("别处.docx")
        self.assert_pass(docx, "--changed", "0")

    def test_without_changed_the_first_check_does_not_run_at_all(self):
        docx = self.半填不留黄("没给.docx")
        r = self.assert_pass(docx)
        self.assertIn("未给 --changed", item_names(r.result, "披露项"))

    def test_a_changed_number_outside_the_file_is_reported(self):
        docx = self.build(name="越界.docx")
        r = self.assert_fail(docx, "改动段号不在这件里", "--changed", "999")
        self.assertIn("p999", r.result["不通过项"][0])

    def test_changed_accepts_the_shape_the_filler_prints(self):
        docx = self.半填不留黄("写法.docx")
        for 写法 in (("--changed", "p2"), ("--changed", "2 3"), ("--changed", "2", "--changed", "3")):
            with self.subTest(写法=写法):
                r = self.gate(docx, *写法)
                self.assertEqual(r.code, 1, r)
        r = support.run(support.GATE, docx, "--json", "--no-render", "--changed", "第二段")
        self.assertEqual(r.code, 2, "读不懂的段号是用法错，不是「文书不合格」")
        self.assertIn("--changed", r.err)


class NormalAndFaultPairs(GateCase):
    """故障样例各一件必拦，正常件必过。"""

    def test_normal_passes_with_disclosures(self):
        docx = self.build()
        r = self.assert_pass(docx, "--template", template("1-2."), "--changed", ",".join(map(str, self.last_changed)))
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

    def test_long_text_in_a_cell_stretches_a_row(self):
        docx = self.stretched_row_docx()
        r = self.assert_fail(docx, "行高超阈值")
        self.assertIn("磅", r.result["不通过项"][0])

    def stretched_row_docx(self):
        """探针：往表格那一格里填越来越长的字，直到推算的下界都超过默认阈值（不写死字数）。"""
        idx = next(i for i, line in enumerate(support.listing(template("1-2.")).out.splitlines())
                   if "[表1 行3 格2]" in line)
        n = 20
        while n <= 2048:
            docx = self.build(None, [{"op": "fill", "at": "p%d#1" % idx, "text": "甲乙丙丁戊己庚辛壬癸" * n}],
                              "撑列-%d.docx" % n)
            if support.gate_no_render(docx).result["推算"]["最大行高"][0] > 200.0:
                return docx
            n *= 2
        raise AssertionError("填到 2 万字都撑不出超阈值的行高")

    def test_blank_page(self):
        good = self.build()
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
        good = self.build()

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
        good = self.build()
        self.assert_pass(good)

        def drop_paragraphs_after_the_last_table(data):
            xml = data.decode("utf-8")
            head, sep, tail = xml.rpartition("</w:tbl>")
            return (head + sep + re.sub(r"<w:p[ >].*?</w:p>|<w:p/>", "", tail, flags=re.S)).encode("utf-8")

        bad = rewrite(good, self.dir / "表接sectPr.docx", {"word/document.xml": drop_paragraphs_after_the_last_table})
        blocks = support.body_blocks(bad)
        self.assertEqual(blocks[-1].tag, W + "tbl", "手术后最后一块须是表")
        self.assert_fail(bad, "表格直接接 sectPr")

    def test_table_wider_than_the_page(self):
        good = self.build()

        def widen(data):
            xml = data.decode("utf-8")
            return re.sub(r'<w:gridCol w:w="\d+"/>', '<w:gridCol w:w="6000"/>', xml).encode("utf-8")

        bad = rewrite(good, self.dir / "表宽.docx", {"word/document.xml": widen})
        self.assert_fail(bad, "表宽超页面")

    def test_template_table_dropped_needs_template(self):
        """模板有表而成品没表即不通过（#107）。

        真事故：模型为了过「行高超阈值」，把模板规定的那张表整个改写成正文段落，几何违规随表一起消失、
        门禁给通过，交出去的是一份缺了正文结构的件。填模板这条路本来就搬不走表，但律师兜底自写的件仍会
        缺表，所以这一项留着。
        """
        tpl = template("1-2.")
        good = self.build(tpl)
        self.assert_pass(good, "--template", tpl)

        def drop_tables(data):
            return re.sub(r"<w:tbl>.*?</w:tbl>", "", data.decode("utf-8"), flags=re.S).encode("utf-8")

        bad = rewrite(good, self.dir / "无表.docx", {"word/document.xml": drop_tables})
        self.assertEqual([b.tag for b in support.body_blocks(bad)].count(W + "tbl"), 0)
        self.assert_fail(bad, "模板表缺失", "--template", tpl)
        r = self.gate(bad)
        self.assertEqual(r.code, 0, "没有模板可比时，成品没表不算错")
        self.assertIn("未给 --template", item_names(r.result, "披露项"))

    def test_page_field_hardcoded_and_missing(self):
        tpl = template("3-1.")
        good = self.build(tpl, name="债权.docx")
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
        """探针：把正文里一段有字的段落复制到翻倍，直到推算下界都超过一页（不写死段数）。"""
        good = self.build(name="一页.docx")
        with zipfile.ZipFile(str(good)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        源 = re.search(r"<w:p [^>]*>(?:(?!<w:p[ >]).)*?苏州工业园区人民法院.*?</w:p>", xml, re.S)
        self.assertIsNotNone(源, "找不到可以复制的正文段")
        n = 8
        while n <= 512:
            def pad(data, n=n):
                xml = data.decode("utf-8")
                return xml.replace("<w:sectPr", 源.group(0) * n + "<w:sectPr", 1).encode("utf-8")

            docx = rewrite(good, self.dir / ("多页-%d.docx" % n), {"word/document.xml": pad})
            if support.gate_no_render(docx).result["推算"]["页数"][0] > 1:
                return docx
            n *= 2
        raise AssertionError("复制到 512 段都推算不出第二页")

    def test_row_height_threshold_is_adjustable(self):
        docx = self.build()
        lo, _ = self.band(docx, "最大行高")
        self.assert_fail(docx, "行高超阈值", "--max-row-height", "%.1f" % (lo / 2))
        self.assert_pass(docx)


class ThreeValuedConclusion(GateCase):
    """需人眼这一档：阈值落在推算区间内，门禁测不准而非测出事故（ADR-0017）。

    这几件恒走无渲染跑道：区间存在的唯一原因就是这台机器上没有渲染器，渲染层一在场这一档当场坍缩。
    """

    def test_threshold_inside_the_band_is_needs_eye_and_still_delivers(self):
        docx = self.build()
        lo, hi = self.band(docx, "最大行高")
        self.assertLess(lo, hi, "推算给的是区间不是点值")
        target = self.dir / "文书" / "印章备案" / "印章备案.docx"
        r = self.assert_needs_eye(docx, "最大行高测不准", "--max-row-height", "%.1f" % lo, "--deliver", target)
        self.assertEqual(r.result["已落盘"], str(target), "需人眼件照常落盘，位置与通过件相同")
        self.assertEqual(target.name, "印章备案.docx", "文件名不加任何装饰")
        self.assertEqual(target.read_bytes(), docx.read_bytes())

    def test_the_regression_fixtures_are_in_the_band_at_the_default_thresholds(self):
        """带内这一档不是靠喂一个凑出来的阈值：这两件在**默认阈值**上就落在带内。

        它们的真值 Word 与 WPS 各量过一列（冻在 `test_layout_estimate.py` 的 FROZEN 里），量的就是
        `fixtures/` 里这两份 docx 本身。推算分不出它们在阈值哪一侧，正是这一档存在的理由。
        """
        cases = (("推算-行高贴阈值.docx", "最大行高测不准", "最大行高"),
                 ("推算-页数贴阈值.docx", "页数测不准", "页数"))
        for name, item, 项名 in cases:
            with self.subTest(件=name):
                docx = self.dir / name
                shutil.copy2(str(support.FIXTURES / name), str(docx))
                target = self.dir / "文书" / name
                r = self.assert_needs_eye(docx, item, "--deliver", target)
                self.assertEqual(r.result["已落盘"], str(target), "需人眼件照常落盘")
                self.assertEqual(target.read_bytes(), docx.read_bytes())
                self.assertIn("- %s：" % 项名, r.result["须目验清单"])

    def test_assert_pass_never_accepts_the_third_grade(self):
        """结论值域每多一档，fixture 必多一件把那一档钉住，且 assert_pass 不得接受该档（ADR-0017）。"""
        docx = self.build()
        lo, _ = self.band(docx, "最大行高")
        with self.assertRaises(AssertionError):
            self.assert_pass(docx, "--max-row-height", "%.1f" % lo)

    def test_needs_eye_report_starts_with_the_checklist(self):
        docx = self.build()
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
        docx = self.半填不留黄()
        lo, _ = self.band(docx, "最大行高")
        target = self.dir / "文书" / "件.docx"
        r = self.assert_fail(docx, "改动段残留占位", "--changed", "2",
                             "--max-row-height", "%.1f" % lo, "--deliver", target)
        self.assertTrue(r.result["需人眼项"], "两档同时在，结论取重的那档")
        self.assertEqual(r.result["须目验清单"], "", "不通过件不落盘，也就没有那份审查报告")
        self.assertFalse(target.exists())


class DeliverAndBackend(GateCase):
    def test_deliver_only_on_pass_and_never_overwrites(self):
        good = self.build()
        target = self.dir / "文书" / "印章备案" / "印章备案.docx"
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

    def test_overwrite_is_how_a_reissue_lands_on_the_same_path(self):
        """一节点一份文书、重出覆盖（ADR-0023）：覆盖要调用方显式点头，脚本自己永不决定。"""
        first = self.build(name="第一版.docx")
        target = self.dir / "文书" / "印章备案" / "印章备案.docx"
        self.assertEqual(self.gate(first, "--deliver", target).code, 0)
        second = self.build(None, [{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], "第二版.docx")
        r = self.gate(second, "--deliver", target, "--overwrite")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.result["已落盘"], str(target))
        self.assertEqual(target.read_bytes(), second.read_bytes(), "落的是第二版")

    def test_fail_means_nothing_is_delivered(self):
        bad = self.半填不留黄()
        target = self.dir / "文书" / "件.docx"
        r = self.gate(bad, "--changed", "2", "--deliver", target)
        self.assertEqual(r.code, 1)
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists(), "不通过连目录都不建")

    def test_lawyer_written_docx_is_checked_the_same_way(self):
        r = self.gate(template("1-2."))
        self.assertEqual(r.code, 1, "官方模板原件带作者与最后修改者，照样报出")
        self.assertIn("元数据残留", support.strip_ws(r.out))
        self.assertTrue(r.result["披露项"], "披露项照给，供审查报告只披露不阻断")
        self.assertIn("未给 --changed", item_names(r.result, "披露项"),
                      "律师兜底自写的件没有改动段，第一样整条不查（ADR-0023）")

    def test_missing_render_backend_still_concludes(self):
        """无渲染后端是主力环境的正常路径，这条跑道必须给出结论（#59 第 9 条，本票反向重写）。"""
        docx = self.build()
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
        r = support.run(support.GATE, self.build(), "--template", self.dir / "没有模板.docx")
        self.assertEqual(r.code, 2)


class NormalAndFaultPairsRendered(NormalAndFaultPairs):
    """同一批用例接上渲染层再跑一遍：点值取代区间。缺渲染通道时整类 skip 并打印说明（ADR-0017）。"""
    EXTRA = ()

    def test_render_point_inside_the_estimated_band(self):
        """渲染点值落在推算区间外要出固定名披露项；本机的正常件不该触发它。"""
        docx = self.build()
        r = self.assert_pass(docx)
        self.assertEqual(r.result["推算区间不含实测值"], [], r.result)
        lo, hi = r.result["推算"]["最大行高"]
        self.assertLessEqual(lo, r.result["渲染"]["最大行高"])
        self.assertLessEqual(r.result["渲染"]["最大行高"], hi)

    def test_highlight_rectangles_are_not_read_as_a_table(self):
        """留黄的件里，一页散开的黄矩形会被 PyMuPDF 的 find_tables 认成一张多行多列的表。

        8-1 的 XML 里一张表都没有，留黄之后却被读出「第 1 页第 1 张表第 1 行 274.4 磅」，整件判不通过
        （#13 在 19 件回归的渲染跑道上撞到）。填模板这条路每一件都带荧光笔，所以这不是偶发：文书自己的
        XML 才知道有没有表、几列，渲出来对不上列数的那些不拿来量行高，只出一条披露项。
        """
        tpl = template("8-1.")
        self.assertEqual(len(read_xml(tpl).find(W + "body").findall(W + "tbl")), 0,
                         "8-1 一张表都没有，这条断言才站得住")
        docx = self.build(tpl, [], "留黄8-1.docx")
        r = self.assert_pass(docx)
        self.assertEqual(r.result["渲染"]["最大行高"], 0.0, "没有表就没有行高：%r" % r.result["渲染"])
        self.assertTrue(any("荧光笔矩形" in n for n in r.result["披露项"]),
                        "认错的表要披露出来，不能静悄悄跳过：%r" % r.result["披露项"])

    def test_render_collapses_the_third_grade(self):
        """渲染层在场时需人眼当场坍缩：同一个带内阈值在这条跑道上只会给出二值。"""
        docx = self.build()
        lo, hi = self.band(docx, "最大行高")
        r = self.gate(docx, "--max-row-height", "%.1f" % lo)
        self.assertIn(r.result["结论"], ("通过", "不通过"))
        self.assertEqual(r.result["需人眼项"], [])


if __name__ == "__main__":
    unittest.main()
