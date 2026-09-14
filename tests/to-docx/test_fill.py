"""skills/in-progress/to-docx/scripts/fill.py 的脚本层单测（unittest）。不需要 Word。

运行：python -m unittest tests/to-docx/test_fill.py

缝是填模板 CLI 的两个子命令：`list` 给一件 DOCX 打出带编号的清单，`apply` 把一份差量原地施加成一件新的
DOCX。造件一律拿官方模板当载体（模板就是出件时的载体），要故障件再在它上面做 XML 手术。

断的是清单的形状（编号、表格坐标、槽、已高亮区间、说明段）、五种差量各自的效果、代码统一留黄、拒改的
那几种（差量不合法、槽所在 run 含脚注引用 / 图片 / 域代码），以及「拒改就一个字都不写」。ADR-0024 搬进施加
构造的三处也在这里：表格后末段的 delete 改清空、fill 空串按没填处理、--out 可覆盖而拒改时原件一字不动。
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

    def test_delete_of_the_last_paragraph_after_the_last_table_clears_it_instead(self):
        """正文最后一张表之后只剩一段时，删了它表格就直接接 sectPr，Word 会报修复：这一种也改清空（ADR-0024）。"""
        src, idx = support.ending_with_a_table(self.tpl, self.dir / "表后末段.docx")
        before = support.paragraph_count(src)
        r = self.ok([{"op": "delete", "at": "p%d" % idx}], "表后清空.docx", src)
        self.assertIn("清空（不能整段删）", r.out)
        out = support.out_path(r)
        self.assertEqual(support.paragraph_count(out), before)
        self.assertEqual(self.文字(out, idx), "")
        last = support.body_blocks(out)[-1]
        self.assertEqual(last.tag, W + "p", "表之后仍有一段，sectPr 不直接接表")

    def test_delete_of_a_paragraph_after_a_table_that_is_not_the_last_still_removes_it(self):
        """同一位置、后面还有别的段：照常删。守的只是「表直接接 sectPr」这一种，不是表后的每一段。"""
        idx, 表后段数 = support.first_paragraph_after_last_table(self.tpl)
        self.assertGreater(表后段数, 1, "这件模板表后要有不止一段，这条才成立")
        before = support.paragraph_count(self.tpl)
        r = self.ok([{"op": "delete", "at": "p%d" % idx}], "表后照删.docx")
        self.assertIn("删段", r.out)
        self.assertEqual(support.paragraph_count(support.out_path(r)), before - 1)

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
        """删了段，后面的段号整体前移；回显的改动段号必须是写出来那件里的，模型照它抄进审查报告。"""
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

    def test_replace_with_an_empty_string_removes_the_text_but_cannot_also_highlight(self):
        """replace 空串是条件块取舍的正当用法，照旧删掉那一处；删掉的东西没法标黄，再带 highlight 就拒。"""
        self.assert_refused([{"op": "replace", "at": "p3", "old": "（如有）", "new": "", "highlight": True}],
                            "没有东西可标")
        r = self.ok([{"op": "replace", "at": "p3", "old": "（如有）", "new": ""}], "换成空.docx")
        self.assertNotIn("（如有）", 填.text_of(填.paragraphs(support.Document(str(support.out_path(r))))[3]))


class EmptyFill(FillCase):
    """fill 空串按「没填」处理（ADR-0024）：槽留原占位、由收尾留黄，不删 run、不拒改。拒改是内容检查，
    #141 的机理正是「检查占位 → 模型删槽过检」。"""

    def test_fill_with_an_empty_string_leaves_the_placeholder_and_the_code_highlights_it(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": ""}], "空填.docx")
        self.assertIn("按没填处理", r.out)
        p = 填.paragraphs(support.Document(str(support.out_path(r))))[2]
        self.assertEqual(填.text_of(p), 填.text_of(填.paragraphs(support.Document(str(self.tpl)))[2]), "文字一个字不动")
        s, e, 原文 = 填.slots(p)[0]
        self.assertEqual(原文, "XX年X月X日")
        self.assertTrue(any(a <= s and e <= b for a, b in 填.highlight_ranges(p)), "没填的槽由收尾留黄")
        self.assertEqual(r.changed, [], "什么都没改，不算改动段")

    def test_fill_with_an_empty_string_and_highlight_is_not_refused_either(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "", "highlight": True}], "空填带黄.docx")
        self.assertIn("按没填处理", r.out)
        p = 填.paragraphs(support.Document(str(support.out_path(r))))[2]
        self.assertEqual(填.slots(p)[0][2], "XX年X月X日")


class OutPath(FillCase):
    """--out 可直接写 文书/ 下的路径并覆盖（重出覆盖同一份）；拒改一个字不写，靠构造成立（ADR-0024）。"""

    def test_out_overwrites_an_existing_file(self):
        self.ok([{"op": "fill", "at": "p2#1", "text": "第一次"}], "同一份.docx")
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "第二次"}], "同一份.docx")
        text = 填.text_of(填.paragraphs(support.Document(str(self.dir / "同一份.docx")))[2])
        self.assertIn("第二次", text)
        self.assertNotIn("第一次", text)
        self.assertEqual(r.changed, [2])

    def test_reissue_may_write_over_its_own_carrier(self):
        """重出时载体就是这个节点当前的文书，产物也落回同一路径。"""
        first = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"}], "当前.docx")
        carrier = support.out_path(first)
        # 载体换成当前文书后槽号重新数：上一次填掉了 #1，原来的 #3 现在是 #2
        r = apply(carrier, [{"op": "fill", "at": "p2#2", "text": "一"}], carrier)
        self.assertEqual(r.code, 0, r)
        text = 填.text_of(填.paragraphs(support.Document(str(carrier)))[2])
        self.assertIn("某年某月某日", text, "上一次填的还在")
        self.assertIn("苏0591破一号", text, "这一次填的也在")

    def test_a_refused_diff_leaves_the_existing_file_byte_for_byte(self):
        self.ok([{"op": "fill", "at": "p2#1", "text": "某"}], "已有.docx")
        before = (self.dir / "已有.docx").read_bytes()
        r = self.apply([{"op": "fill", "at": "p2#99", "text": "某"}], "已有.docx")
        self.assertEqual(r.code, 1, r)
        self.assertEqual((self.dir / "已有.docx").read_bytes(), before, "拒改的件一个字都不写，已有的那份原样")
        self.assertFalse((self.dir / "已有.docx.part").exists())


class Metadata(FillCase):
    def test_metadata_is_cleared_on_the_way_out(self):
        """官方模板原件带作者与上次打印时间；apply 收尾无条件清掉，这是施加的构造、不是一条检查（ADR-0024）。"""
        core = read_xml(self.tpl, "docProps/core.xml")
        self.assertTrue((core.find(support.DC + "creator").text or "").strip(), "模板原件本来有作者")
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某"}], "元数据.docx")
        self.assertEqual(support.metadata_leftovers(support.out_path(r)), [])


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


class HighlightList(FillCase):
    """apply 回显末尾的高亮清单（#14）：一处一行，记段落号（提示用）、高亮处原文、记录时整段文字，不记偏移。
    它是给模型下次重出读的：对照当前文书清单里的 ⟪⟫ 判律师填没填（判断归模型，ADR-0024）。"""

    def _list(self, stdout):
        lines = stdout.splitlines()
        head = next(i for i, l in enumerate(lines) if l.startswith("高亮清单 "))
        n = int(re.match(r"高亮清单 (\d+) 处", lines[head]).group(1))
        return n, lines[head + 1:]

    def _ranges(self, docx):
        doc = support.Document(str(docx))
        out = []
        for idx, p in enumerate(填.paragraphs(doc)):
            t = 填.text_of(p)
            where = 填._where(p, doc).strip()
            for s, e in 填.highlight_ranges(p):
                out.append((idx, where, t[s:e], t))
        return out

    def _head(self, idx, where):
        return "p%d%s" % (idx, " " + where if where else "")

    def test_the_list_covers_every_highlight_in_the_file_that_was_written(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某年某月某日"},
                     {"op": "fill", "at": "p2#9", "text": "某所", "highlight": True},
                     {"op": "highlight", "at": "p10", "text": "特此报告"}])
        n, lines = self._list(r.out)
        expected = self._ranges(support.out_path(r))
        self.assertEqual(n, len(expected), r.out)
        self.assertEqual(len(lines), n, "一处一行，清单之后不再有别的行")
        for (idx, where, 原文, 整段), line in zip(expected, lines):
            self.assertEqual(line, "%s「%s」｜%s" % (self._head(idx, where), 原文, 整段), r.out)
        self.assertTrue(any(l.startswith("p9 [表1 行3 格2]「") for l in lines), "单元格里的段带表格坐标当键：\n%s" % r.out)
        self.assertTrue(any("「某所」" in l for l in lines), "模型带黄填的那处也在清单里")
        self.assertTrue(any("「特此报告」" in l for l in lines), "模型加黄的那句也在清单里")
        self.assertFalse(any("「某年某月某日」" in l for l in lines), "填了没带黄的不在清单里")

    def test_the_list_is_numbered_by_the_file_that_was_written(self):
        r = self.ok([{"op": "delete", "at": "p10"}], "删段.docx")
        _, lines = self._list(r.out)
        expected = self._ranges(support.out_path(r))
        self.assertEqual([l.split("「", 1)[0] for l in lines], [self._head(idx, w) for idx, w, _, _ in expected])

    def test_template_highlights_stay_listed_until_unhighlighted(self):
        tpl = template(带自带高亮的模板)
        kept = self.ok([], "留着.docx", tpl)
        _, lines = self._list(kept.out)
        inherited = [(idx, w, 原文) for idx, w, 原文, _ in self._ranges(tpl)]
        self.assertTrue(inherited)
        for idx, w, 原文 in inherited:
            self.assertTrue(any(l.startswith("%s「%s」｜" % (self._head(idx, w), 原文)) for l in lines), "模板自带的黄没进清单：%s" % 原文)
        idx, w, 原文 = inherited[0]
        gone = self.ok([{"op": "unhighlight", "at": "p%d" % idx, "text": 原文}], "去了.docx", tpl)
        _, lines = self._list(gone.out)
        self.assertFalse(any(l.startswith("%s「%s」｜" % (self._head(idx, w), 原文)) for l in lines), "去了黄的不该还在清单里")

    def test_one_line_per_highlight_even_with_a_line_break_inside(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "甲\n乙", "highlight": True}], "换行.docx")
        n, lines = self._list(r.out)
        self.assertEqual(len(lines), n)
        line = next(l for l in lines if l.startswith("p2「"))
        self.assertIn("甲⏎乙", line, "换行写成 ⏎，一处仍是一行")

    def test_no_highlight_rest_still_lists_what_is_yellow(self):
        r = self.ok([{"op": "fill", "at": "p2#1", "text": "某", "highlight": True}], "不留黄.docx", None, "--no-highlight-rest")
        n, lines = self._list(r.out)
        self.assertEqual(n, 1, r.out)
        self.assertTrue(lines[0].startswith("p2「某」｜"))

    def test_json_output_carries_the_list(self):
        out = self.dir / "json.docx"
        diff = self.dir / "j.json"
        diff.write_text(json.dumps([{"op": "fill", "at": "p2#1", "text": "某", "highlight": True}], ensure_ascii=False), encoding="utf-8")
        r = support.run(support.FILL, "apply", self.tpl, "--diff", diff, "--out", out, "--json")
        self.assertEqual(r.code, 0, r)
        got = json.loads(r.out)["高亮清单"]
        self.assertEqual(len(got), len(self._ranges(out)))
        self.assertEqual(sorted(got[0]), ["p", "原文", "整段", "格"])
        self.assertEqual(got[0]["p"], 2)
        self.assertEqual(got[0]["格"], "", "正文段的表格坐标是空串")
        self.assertTrue(any(x["格"] == "表1 行3 格2" for x in got), "单元格段带表格坐标")
        self.assertEqual(got[0]["原文"], "某")
        self.assertEqual(got[0]["整段"], 填.text_of(填.paragraphs(support.Document(str(out)))[2]))


if __name__ == "__main__":
    unittest.main()
