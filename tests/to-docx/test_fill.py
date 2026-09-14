"""skills/in-progress/to-docx/scripts/fill.py 的脚本层单测（unittest）。不需要 Word。

运行：python -m unittest tests/to-docx/test_fill.py

缝是填模板 CLI 的两个子命令：`list` 给一件 DOCX 打出带编号的清单，`apply` 把一份差量原地施加成一件新的
DOCX。造件一律拿官方模板当载体（模板就是出件时的载体），要故障件再在它上面做 XML 手术。

断的是清单的形状（编号、表格坐标、槽、已高亮区间、说明段）、五种差量各自的效果、代码统一留黄、拒改的
那几种（差量不合法、槽所在 run 含脚注引用 / 图片 / 域代码），以及「拒改就一个字都不写」。
"""
import json
import pathlib
import re
import shutil
import tempfile
import unittest

import support
from support import W, apply, fill_all_ops, listing, read_xml, rewrite, slots_of, template, 填

带说明段的模板 = "4-2."     # 首段是「（注：…）」
带自带高亮的模板 = "4-1."   # 19 件里有 9 件自带黄色高亮，标的是条件块与提示句


class FillCase(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-fill-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.tpl = template("1-2.")

    def apply(self, ops, name="件.docx", src=None, *extra):
        return apply(src or self.tpl, ops, self.dir / name, *extra)

    def ok(self, ops, name="件.docx", src=None, *extra):
        r = self.apply(ops, name, src, *extra)
        self.assertEqual(r.code, 0, r)
        return r


class Listing(FillCase):
    def test_every_paragraph_is_numbered_in_document_order(self):
        r = listing(self.tpl)
        self.assertEqual(r.code, 0, r)
        lines = r.out.splitlines()
        self.assertEqual(len(lines), support.paragraph_count(self.tpl), "一段一行，单元格里的段落也在序列里")
        for i, line in enumerate(lines):
            self.assertTrue(line.startswith("p%d " % i), "第 %d 行的编号不对：%r" % (i, line))

    def test_cell_paragraphs_carry_table_row_cell(self):
        line = next(l for l in listing(self.tpl).out.splitlines() if "[表" in l)
        self.assertRegex(line, r"^p\d+ \[表\d+ 行\d+ 格\d+\] ")

    def test_slots_are_numbered_left_to_right_inside_the_paragraph(self):
        idx, sl = slots_of(self.tpl)[0]
        line = next(l for l in listing(self.tpl).out.splitlines() if l.startswith("p%d " % idx))
        for n, (_, _, 原文) in enumerate(sl, 1):
            self.assertIn("⟦%d %s⟧" % (n, 原文), line)
        self.assertLess(line.index("⟦1 "), line.index("⟦2 "), "槽按从左到右编号")

    def test_template_highlights_show_up_as_a_marked_range(self):
        r = listing(template(带自带高亮的模板))
        self.assertEqual(r.code, 0, r)
        self.assertIn("⟪", r.out, "模板自带的黄色要在清单里看得见（19 件里有 24 处）")
        self.assertIn("⟫", r.out)

    def test_note_paragraphs_are_tagged(self):
        r = listing(template(带说明段的模板))
        self.assertTrue(any("[说明] " in l for l in r.out.splitlines()), r.out[:400])

    def test_plain_is_the_same_text_without_a_single_marker(self):
        marked = listing(self.tpl)
        plain = listing(self.tpl, "--plain")
        self.assertEqual(plain.code, 0, plain)
        self.assertEqual(len(plain.out.splitlines()), len(marked.out.splitlines()))
        for ch in ("⟦", "⟧", "⟪", "⟫", "[表", "[说明]"):
            self.assertNotIn(ch, plain.out)
        self.assertIn("苏州工业园区人民法院", plain.out, "纯文本仍是这一件的正文")

    def test_broken_file_is_refused_not_crashed(self):
        broken = self.dir / "坏.docx"
        broken.write_bytes(b"not a zip")
        r = listing(broken)
        self.assertEqual(r.code, 1, r)
        self.assertIn("打不开", r.err)
        self.assertEqual(listing(self.dir / "没有.docx").code, 1)


class SlotShapes(FillCase):
    """占位形状：出厂 19 件里的槽都认得出，且形状可加。"""

    def test_the_factory_shapes_cover_the_odd_ones_in_the_nineteen_templates(self):
        found = {}
        for tpl in support.all_templates():
            for _, sl in slots_of(tpl):
                for _, _, 原文 in sl:
                    if 原文 == "X":   # 量词是前瞻，不进槽本身：「X家债权人」的槽就是那一个 X
                        found.setdefault("量词前的单个 X", 原文)
                    elif 原文.startswith("【") and len(原文) > 40:
                        found.setdefault("整段条件块", 原文)
                    elif "年" in 原文 and "月" in 原文:
                        found.setdefault("日期", 原文)
                    elif 原文.startswith("（20"):
                        found.setdefault("案号年份", 原文)
        for 形状 in ("量词前的单个 X", "整段条件块", "日期", "案号年份"):
            self.assertIn(形状, found, "19 件模板里这种形状一个都没认出来：%s（认出的：%r）" % (形状, found))

    def test_a_shape_can_be_added_for_one_run(self):
        赞 = "〈本案金额〉"
        ops = [{"op": "replace", "at": "p10", "old": "特此报告", "new": "特此报告" + 赞}]
        out = self.ok(ops, "加形状.docx")
        默认 = listing(support.out_path(out))
        self.assertNotIn("⟦1 〈本案金额〉⟧", 默认.out, "默认形状不该认得这种占位")
        加了 = listing(support.out_path(out), "--slot-pattern", r"〈[^〉]*〉")
        self.assertIn("〈本案金额〉⟧", 加了.out, "--slot-pattern 加的形状要进清单：%r" % 加了.out[:300])

    def test_the_two_clis_carry_the_same_table(self):
        """两个 CLI 互不 import，各自带一份占位表；两份必须逐字相同，不然门禁与清单会看见不同的槽。"""
        import sys
        sys.path.insert(0, str(support.SCRIPTS))
        import gate
        self.assertEqual(填.SLOT_SHAPES, gate.SLOT_SHAPES)


class ApplyFive(FillCase):
    """五种差量各自的效果。"""

    def 文字(self, docx, idx):
        return 填.text_of(填.paragraphs(support.Document(str(docx)))[idx])

    def test_fill_puts_the_text_in_the_slot(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"}])
        out = support.out_path(r)
        self.assertIn("于某年某月某日作出", self.文字(out, 2))
        self.assertEqual(r.changed, [2])

    def test_fill_with_highlight_keeps_the_new_text_yellow(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日", "highlight": True}])
        out = support.out_path(r)
        p = 填.paragraphs(support.Document(str(out)))[2]
        text = 填.text_of(p)
        亮 = [text[a:b] for a, b in 填.highlight_ranges(p)]
        self.assertIn("某年某月某日", 亮, "填了但没把握的要仍是黄的：%r" % 亮)

    def test_replace_needs_the_old_text_to_be_unique(self):
        r = self.ok([{"op": "replace", "at": "p2", "old": "XX公司（债权人名称）", "new": "某甲公司"}])
        out = support.out_path(r)
        self.assertIn("裁定受理某甲公司申请", self.文字(out, 2))
        bad = self.apply([{"op": "replace", "at": "p2", "old": "XX", "new": "某"}], "不唯一.docx")
        self.assertEqual(bad.code, 1, bad)
        self.assertIn("须唯一", bad.err)

    def test_delete_removes_the_paragraph(self):
        before = support.paragraph_count(self.tpl)
        r = self.ok([{"op": "delete", "at": "p14"}])
        out = support.out_path(r)
        self.assertEqual(support.paragraph_count(out), before - 1)
        self.assertNotIn("（盖章）", 填.plain_text(support.Document(str(out))))

    def test_delete_of_a_cells_only_paragraph_clears_it_instead(self):
        """单元格至少要有一个 w:p，带 sectPr 的段也删不得：这两种改成清空文字，表格的形不变。"""
        idx = next(i for i, line in enumerate(listing(self.tpl).out.splitlines()) if "[表1 行3 格2]" in line)
        before = support.paragraph_count(self.tpl)
        r = self.ok([{"op": "delete", "at": "p%d" % idx}], "清空.docx")
        self.assertIn("清空（不能整段删）", r.out)
        out = support.out_path(r)
        self.assertEqual(support.paragraph_count(out), before, "段数不变，只是那一段没字了")
        self.assertEqual(self.文字(out, idx), "")

    def test_highlight_and_unhighlight(self):
        r = self.ok([{"op": "highlight", "at": "p10", "text": "特此报告"}])
        out = support.out_path(r)
        p = 填.paragraphs(support.Document(str(out)))[10]
        self.assertEqual([填.text_of(p)[a:b] for a, b in 填.highlight_ranges(p)], ["特此报告"])

        r2 = apply(out, [{"op": "unhighlight", "at": "p10", "text": "特此报告"}], self.dir / "去黄.docx")
        self.assertEqual(r2.code, 0, r2)
        p2 = 填.paragraphs(support.Document(str(self.dir / "去黄.docx")))[10]
        self.assertEqual(填.highlight_ranges(p2), [], "去黄之后那一段一处黄都不剩")

    def test_several_changes_in_one_paragraph_land_where_they_should(self):
        """同一段的改动按区间从后往前施加，前面几处的偏移不受影响。"""
        ops = [{"op": "fill", "at": "p2#1", "text": "某年某月某日"},
               {"op": "fill", "at": "p2#3", "text": "一"},
               {"op": "fill", "at": "p2#11", "text": "某乙"},
               {"op": "replace", "at": "p2", "old": "XX公司（债权人名称）", "new": "某甲公司"}]
        r = self.ok(ops, "多处.docx")
        text = self.文字(support.out_path(r), 2)
        self.assertIn("于某年某月某日作出", text)
        self.assertIn("苏0591破一号裁定书", text)
        self.assertIn("裁定受理某甲公司申请", text)
        self.assertTrue(text.endswith("负责人为某乙。"), text)


class HighlightRest(FillCase):
    def test_code_highlights_every_slot_nobody_touched(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"}])
        out = support.out_path(r)
        self.assertIn("代码留黄", r.out)
        doc = support.Document(str(out))
        for idx, p in enumerate(填.paragraphs(doc)):
            hl = 填.highlight_ranges(p)
            for s, e, 原文 in 填.slots(p):
                self.assertTrue(any(a <= s and e <= b for a, b in hl),
                                "p%d 的槽「%s」没被留黄" % (idx, 原文))

    def test_filled_slots_are_not_highlighted_again(self):
        r = self.ok(fill_all_ops(self.tpl), "全填.docx")
        out = support.out_path(r)
        self.assertIn("代码留黄 0 处", r.out)
        doc = support.Document(str(out))
        for p in 填.paragraphs(doc):
            self.assertEqual(填.slots(p), [], "全填之后一个槽都不该剩")

    def test_no_highlight_rest_leaves_them_alone(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], "不留黄.docx", None, "--no-highlight-rest")
        out = support.out_path(r)
        self.assertIn("代码留黄 0 处", r.out)
        p = 填.paragraphs(support.Document(str(out)))[2]
        self.assertEqual(填.highlight_ranges(p), [], "说了不留黄就一处都不加")


class ChangedParagraphs(FillCase):
    def test_changed_numbers_are_the_ones_in_the_file_that_was_written(self):
        """删了段，后面的段号整体前移；回显的改动段号必须是写出来那件里的，门禁按它去查。"""
        r = self.ok([{"op": "delete", "at": "p10"}, {"op": "fill", "at": "p13#1", "text": "某乙"}], "飘.docx")
        self.assertEqual(r.changed, [12], r.out)
        out = support.out_path(r)
        self.assertIn("某乙", 填.text_of(填.paragraphs(support.Document(str(out)))[12]))

    def test_only_the_paragraphs_the_model_touched_are_reported(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], "只报改动.docx")
        self.assertEqual(r.changed, [2], "代码留黄的那些段不算改动段（律师要动手的位置本来就留着占位）")

    def test_an_empty_diff_only_highlights(self):
        r = self.ok([], "只留黄.docx")
        self.assertEqual(r.changed, [])
        self.assertIn("代码留黄", r.out)


class Refusals(FillCase):
    """拒改：退出码 1，stderr 说清楚，产物一个字都不写。"""

    def assert_refused(self, ops, 关键词, name="拒.docx", src=None, *extra):
        r = self.apply(ops, name, src, *extra)
        self.assertEqual(r.code, 1, r)
        self.assertIn(关键词, r.err, r)
        self.assertFalse((self.dir / name).exists(), "拒改的件不许落下半成品")
        return r

    def test_slot_number_out_of_range(self):
        self.assert_refused([{"op": "fill", "at": "p2#99", "text": "某"}], "没有 #99")

    def test_paragraph_out_of_range(self):
        self.assert_refused([{"op": "fill", "at": "p999#1", "text": "某"}], "没有 p999")

    def test_overlapping_ranges(self):
        self.assert_refused([{"op": "fill", "at": "p2#1", "text": "某"},
                             {"op": "replace", "at": "p2", "old": "于XX年X月X日作出", "new": "某"}], "区间重叠")

    def test_unknown_op_and_bad_at(self):
        self.assert_refused([{"op": "rewrite", "at": "p2"}], "没有 'rewrite' 这种改动")
        self.assert_refused([{"op": "fill", "at": "第二段", "text": "某"}], "位置写法不对", "拒2.docx")

    def test_fill_needs_a_slot_number_and_a_text(self):
        self.assert_refused([{"op": "fill", "at": "p2", "text": "某"}], "要写槽号")
        self.assert_refused([{"op": "fill", "at": "p2#1"}], "缺 text", "拒2.docx")

    def test_diff_must_be_a_json_array(self):
        out = self.dir / "坏差量.docx"
        diff = self.dir / "坏.json"
        diff.write_text("{不是 JSON", encoding="utf-8")
        r = support.run(support.FILL, "apply", self.tpl, "--diff", diff, "--out", out)
        self.assertEqual(r.code, 1, r)
        self.assertIn("不是合法 JSON", r.err)
        diff.write_text(json.dumps({"op": "fill"}), encoding="utf-8")
        r = support.run(support.FILL, "apply", self.tpl, "--diff", diff, "--out", out)
        self.assertEqual(r.code, 1, r)
        self.assertIn("要是一个数组", r.err)

    def test_a_run_with_a_field_code_is_refused_by_name(self):
        """槽所在 run 含域代码、脚注引用或图片时拒改：切开 run 要深拷贝，拷贝会把它复制、换字会把它丢掉。"""
        for 子元素, 人话 in (('<w:fldChar w:fldCharType="begin"/>', "域代码"),
                          ('<w:footnoteReference w:id="1"/>', "脚注引用"),
                          ('<w:drawing/>', "图片")):
            with self.subTest(子元素=子元素):
                def inject(data, 子=子元素):
                    xml = data.decode("utf-8")
                    i = xml.index("<w:t>XX</w:t>")
                    return (xml[:i] + 子 + xml[i:]).encode("utf-8")

                bad = rewrite(self.tpl, self.dir / "含域代码.docx", {"word/document.xml": inject})
                r = self.assert_refused([{"op": "fill", "at": "p2#2", "text": "某"}], 人话, "拒-%s.docx" % 人话, bad)
                self.assertIn("拒改", r.err)

    def test_emptying_a_spot_and_highlighting_it_is_refused(self):
        """换成空串是把那一处删掉，删掉的东西没法标黄：与其把 highlight 悄悄吞掉，不如拒掉。"""
        self.assert_refused([{"op": "replace", "at": "p3", "old": "（如有）", "new": "", "highlight": True}],
                            "没有东西可标")
        r = self.ok([{"op": "replace", "at": "p3", "old": "（如有）", "new": ""}], "换成空.docx")
        self.assertNotIn("（如有）", 填.text_of(填.paragraphs(support.Document(str(support.out_path(r))))[3]))

    def test_output_is_never_overwritten(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某"}], "占位.docx")
        self.assertEqual(r.code, 0)
        again = self.apply([{"op": "fill", "at": "p2#1", "text": "某"}], "占位.docx")
        self.assertEqual(again.code, 1, again)
        self.assertIn("不覆盖", again.err)


class Metadata(FillCase):
    def test_metadata_is_cleared_on_the_way_out(self):
        """官方模板原件带作者与上次打印时间；出件这一步照现有规则清掉（通用裁定台账 #10）。"""
        core = read_xml(self.tpl, "docProps/core.xml")
        self.assertTrue((core.find(support.DC + "creator").text or "").strip(), "模板原件本来有作者")
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某"}], "元数据.docx")
        out = support.out_path(r)
        core = read_xml(out, "docProps/core.xml")
        self.assertFalse((core.find(support.DC + "creator").text or "").strip())
        self.assertFalse((core.find(support.CP + "lastModifiedBy").text or "").strip())
        self.assertIsNone(core.find(support.CP + "lastPrinted"))


class TempOutput(FillCase):
    def test_without_out_it_writes_to_the_temp_dir_and_prints_the_path(self):
        diff = self.dir / "差量.json"
        diff.write_text(json.dumps([{"op": "fill", "at": "p2#1", "text": "某"}], ensure_ascii=False), encoding="utf-8")
        r = support.run(support.FILL, "apply", self.tpl, "--diff", diff)
        self.assertEqual(r.code, 0, r)
        out = support.out_path(r)
        self.addCleanup(lambda: out.exists() and out.unlink())
        self.assertTrue(out.is_file(), r.out)
        self.assertEqual(out.parent.name, "to-docx", "工作区里不建暂存目录，中间件落在 %TEMP%/to-docx/")

    def test_the_environment_line_sits_on_the_second_line(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某"}], "环境.docx")
        lines = r.out.splitlines()
        self.assertTrue(lines[0].startswith("已写出 "), r.out)
        self.assertTrue(lines[1].startswith("出件环境："), r.out)
        self.assertTrue(lines[2].startswith("改动段："), r.out)

    def test_json_output_carries_the_same_four_things(self):
        out = self.dir / "json.docx"
        diff = self.dir / "j.json"
        diff.write_text(json.dumps([{"op": "fill", "at": "p2#1", "text": "某"}], ensure_ascii=False), encoding="utf-8")
        r = support.run(support.FILL, "apply", self.tpl, "--diff", diff, "--out", out, "--json")
        self.assertEqual(r.code, 0, r)
        got = json.loads(r.out)
        self.assertEqual(got["产物"], str(out))
        self.assertEqual(got["改动段"], [2])
        self.assertTrue(got["出件环境"].startswith("出件环境："))
        self.assertTrue(got["留黄"])


if __name__ == "__main__":
    unittest.main()
