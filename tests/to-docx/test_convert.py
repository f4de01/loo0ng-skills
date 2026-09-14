"""skills/productivity/to-docx/scripts/md2docx.py 的脚本层单测（unittest）。不需要 Word。

运行：python -m unittest tests/to-docx/test_convert.py

缝是转换器 CLI：给一段最小集 Markdown 与一件官方模板，断言写出的 DOCX 的 XML（段落格式、表的形、收尾两条规则）。
稿子全是甲乙丙占位，没有案件内容（ADR-0015）。
"""
import datetime
import os
import pathlib
import shutil
import tempfile
import unittest

import support
from support import W, CP, DC, FIXTURES, body_blocks, convert, read_xml, table_signature, template, text_of


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def ppr(p):
    return p.find(W + "pPr")


def jc(p):
    el = ppr(p).find(W + "jc") if ppr(p) is not None else None
    return el.get(W + "val") if el is not None else None


def first_line(p):
    ind = ppr(p).find(W + "ind") if ppr(p) is not None else None
    return ind.get(W + "firstLine") if ind is not None else None


def first_rpr(p):
    for r in p.iter(W + "r"):
        rpr = r.find(W + "rPr")
        if rpr is not None:
            return rpr
    return None


def font(p):
    rpr = first_rpr(p)
    rf = rpr.find(W + "rFonts") if rpr is not None else None
    return rf.get(W + "eastAsia") if rf is not None else None


def size(p):
    rpr = first_rpr(p)
    sz = rpr.find(W + "sz") if rpr is not None else None
    return sz.get(W + "val") if sz is not None else None


class ConvertCase(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-test-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.out = self.dir / "出件.docx"

    def convert(self, markdown, tpl):
        r = convert(markdown, tpl, self.out)
        self.assertEqual(r.code, 0, r)
        self.assertTrue(self.out.is_file())
        self.assertIn("已写出", r.out)
        return r

    # ---------------------------------------------------------------- 最小集

    def test_blocks_take_template_formatting(self):
        self.convert(fixture("印章备案.md"), template("1-2."))
        blocks = body_blocks(self.out)
        title = blocks[0]
        self.assertEqual(text_of(title), "关于管理人印章备案的报告")
        self.assertEqual(jc(title), "center")
        self.assertEqual(font(title), "方正小标宋简体")
        self.assertEqual(size(title), "36")
        salutation = blocks[1]
        self.assertEqual(text_of(salutation), "甲法院：")
        self.assertIsNone(first_line(salutation), ":left: 段不该有首行缩进")
        self.assertEqual(font(salutation), "仿宋")
        body = blocks[2]
        self.assertEqual(first_line(body), "640", "正文段照模板首行缩进两字")
        self.assertEqual(size(body), "32")
        rights = [b for b in blocks if b.tag == W + "p" and jc(b) == "right"]
        self.assertEqual([text_of(b) for b in rights], ["乙公司管理人", "（盖章）", "甲年乙月丙日"])
        tpl_right = [p for p in read_xml(template("1-2.")).find(W + "body").findall(W + "p") if jc(p) == "right"][0]
        self.assertEqual(first_line(rights[0]), first_line(tpl_right), "右对齐段的缩进照模板，不自作主张")

    def test_one_line_is_one_paragraph_and_blank_lines_make_nothing(self):
        self.convert("# 题\n\n\n\n第一段\n第二段\n\n第三段\n", template("1-2."))
        texts = [text_of(b) for b in body_blocks(self.out)]
        self.assertEqual(texts, ["题", "第一段", "第二段", "第三段"])

    def test_template_body_is_cleared(self):
        self.convert(fixture("印章备案.md"), template("1-2."))
        whole = "".join(text_of(b) for b in body_blocks(self.out))
        self.assertNotIn("XX", whole)
        self.assertNotIn("苏州", whole)

    def test_rejects_syntax_outside_the_minimal_set(self):
        for bad, why in (("## 二级标题", "多级标题"), ("```\nx\n```", "代码块"), ("- 项目", "列表"),
                         ("有**加粗**的段", "加粗"), ("> 引用", "引用"), (":center: 居中", "前缀"), ("#没有空格", "一级标题")):
            r = convert("# 题\n\n" + bad + "\n", template("1-2."), self.out)
            self.assertEqual(r.code, 1, (bad, r))
            self.assertIn("不在最小集", r.err)
            self.assertIn(why, r.err)
            self.assertFalse(self.out.exists(), "拒绝时什么都不写")

    def test_numbered_lines_are_plain_paragraphs(self):
        self.convert("# 题\n\n一、第一项\n\n1. 第一点\n\n（一）小项\n", template("1-2."))
        self.assertEqual([text_of(b) for b in body_blocks(self.out)][1:], ["一、第一项", "1. 第一点", "（一）小项"])

    def test_empty_markdown_is_rejected(self):
        r = convert("\n\n", template("1-2."), self.out)
        self.assertEqual(r.code, 1)
        self.assertIn("空", r.err)

    # ---------------------------------------------------------------- 表格照抄模板

    def test_template_table_keeps_grid_heights_and_cell_format(self):
        tpl = template("1-2.")
        self.convert(fixture("印章备案.md"), tpl)
        tpl_tbl = read_xml(tpl).find(W + "body").find(W + "tbl")
        out_tbl = [b for b in body_blocks(self.out) if b.tag == W + "tbl"][0]
        self.assertEqual(table_signature(out_tbl), table_signature(tpl_tbl))
        rows = out_tbl.findall(W + "tr")
        self.assertEqual([text_of(tc) for tc in rows[1].findall(W + "tc")], ["印模", ""])
        self.assertEqual(font(rows[0].findall(W + "tc")[0].find(W + "p")), font(tpl_tbl.findall(W + "tr")[0].findall(W + "tc")[0].find(W + "p")))

    def test_merges_follow_the_convention(self):
        tpl = template("3-1.")
        self.convert(fixture("债权确认.md"), tpl)
        tbl = [b for b in body_blocks(self.out) if b.tag == W + "tbl"][0]
        sig = table_signature(tbl)
        self.assertEqual(sig[0], table_signature(read_xml(tpl).find(W + "body").find(W + "tbl"))[0], "列宽照抄")
        rows = sig[1]
        self.assertEqual(rows[3][1][0], ("1", "restart"))
        self.assertEqual(rows[3][1][1], ("1", "restart"))
        self.assertEqual(rows[4][1][0], ("1", "continue"))
        self.assertEqual(rows[4][1][1], ("1", "continue"))
        self.assertEqual(rows[7][1][0], ("2", None), "合计 行「<」并成 gridSpan=2")
        self.assertEqual(len(rows[7][1]), 4)
        last_cells = tbl.findall(W + "tr")[7].findall(W + "tc")
        self.assertEqual(text_of(last_cells[0]), "合计")
        self.assertEqual(text_of(tbl.findall(W + "tr")[4].findall(W + "tc")[0]), "", "续格没有字")
        self.assertEqual([r[0] for r in rows], [("567", "exact")] * 6 + [("767", "exact"), ("567", "exact")], "行高逐行照抄模板")

    def test_mirrored_fixture_has_the_same_shape_as_the_template(self):
        for prefix in ("1-1.", "3-1.", "3-2.", "8-2."):
            tpl = template(prefix)
            self.out.unlink(missing_ok=True)
            self.convert(support.markdown_mirroring(tpl), tpl)
            tpl_tables = read_xml(tpl).find(W + "body").findall(W + "tbl")
            out_tables = [b for b in body_blocks(self.out) if b.tag == W + "tbl"]
            self.assertEqual(len(out_tables), len(tpl_tables), prefix)
            for a, b in zip(out_tables, tpl_tables):
                self.assertEqual(table_signature(a), table_signature(b), prefix)

    def test_extra_rows_copy_the_last_template_row_and_fewer_rows_are_fine(self):
        tpl = template("8-2.")
        md = "# 题\n\n| 序号 | 项目 | 金额 | 备注 |\n|---|---|---|---|\n| 1 | 甲 | 1 | 无 |\n" + "".join(
            "| %d | 乙 | 2 | 无 |\n" % i for i in range(2, 9)) + "\n结束。\n"
        self.convert(md, tpl)
        tbl = [b for b in body_blocks(self.out) if b.tag == W + "tbl"][0]
        rows = table_signature(tbl)[1]
        self.assertEqual(len(rows), 9)
        self.assertEqual([r[0] for r in rows[:5]], [("396", None), ("396", None), ("438", None), ("791", None), ("409", None)], "前五行逐行照模板")
        self.assertEqual([r[0] for r in rows[5:]], [("409", None)] * 4, "超出模板的行照最后一行的行高")
        self.out.unlink()
        self.convert("# 题\n\n| 序号 | 项目 | 金额 | 备注 |\n|---|---|---|---|\n\n结束。\n", tpl)
        self.assertEqual(len(table_signature([b for b in body_blocks(self.out) if b.tag == W + "tbl"][0])[1]), 1)

    def test_table_shape_errors_are_rejected(self):
        tpl = template("3-1.")
        for bad, why in (("| a | b |\n|---|---|\n| 1 | 2 |\n", "列"),
                         ("| a | b | c | d | e |\n|---|---|---|---|---|\n| < | 1 | 2 | 3 | 4 |\n", "左边没有格"),
                         ("| ^ | b | c | d | e |\n|---|---|---|---|---|\n| 0 | 1 | 2 | 3 | 4 |\n", "上一行"),
                         ("| a | b |\n| 1 | 2 | 3 |\n", "格数须相同")):
            r = convert("# 题\n\n" + bad, tpl, self.out)
            self.assertEqual(r.code, 1, (bad, r))
            self.assertIn(why, r.err)
            self.assertFalse(self.out.exists())

    def test_merge_up_needs_a_cell_starting_at_the_same_column(self):
        r = convert("# 题\n\n| a | b | c |\n|---|---|---|\n| 1 | < | 3 |\n| 4 | ^ | 6 |\n", template("4-1."), self.out)
        self.assertEqual(r.code, 1)
        self.assertIn("上一行同一位置没有格", r.err)

    def test_free_table_when_template_has_none(self):
        tpl = template("4-1.")
        r = self.convert("# 题\n\n| 甲 | 乙 | 丙 |\n|---|---|---|\n| 1 | 2 | 3 |\n\n完。\n", tpl)
        self.assertIn("自由表", r.out)
        tbl = [b for b in body_blocks(self.out) if b.tag == W + "tbl"][0]
        grid = [int(g.get(W + "w")) for g in tbl.find(W + "tblGrid").findall(W + "gridCol")]
        self.assertEqual(len(set(grid)), 1, "等宽")
        self.assertLessEqual(sum(grid), 11906 - 1800 - 1800)
        self.assertIsNotNone(tbl.find(W + "tblPr").find(W + "tblBorders"))
        self.assertEqual(font(tbl.findall(W + "tr")[0].findall(W + "tc")[0].find(W + "p")), "仿宋")

    def test_second_table_beyond_template_count_is_free(self):
        r = self.convert(fixture("撑列.md"), template("1-2."))
        self.assertIn("第 1 张表照抄模板", r.out)
        self.assertIn("第 2 张表模板里没有对应的表", r.out)

    # ---------------------------------------------------------------- 收尾两条规则

    def test_trailing_table_gets_an_empty_paragraph(self):
        r = self.convert("# 题\n\n| 印章名称 | 甲 |\n|---|---|\n", template("1-2."))
        blocks = body_blocks(self.out)
        self.assertEqual(blocks[-2].tag, W + "tbl")
        self.assertEqual(blocks[-1].tag, W + "p")
        self.assertEqual(text_of(blocks[-1]), "")
        self.assertIn("表后补了一个空段", r.out)

    def test_no_empty_paragraph_when_text_ends_the_document(self):
        self.convert(fixture("印章备案.md"), template("1-2."))
        blocks = body_blocks(self.out)
        self.assertEqual(text_of(blocks[-1]), "甲年乙月丙日")

    def test_metadata_is_cleared(self):
        self.convert(fixture("印章备案.md"), template("1-2."))
        core = read_xml(self.out, "docProps/core.xml")
        self.assertEqual(core.find(DC + "creator").text or "", "")
        self.assertEqual(core.find(CP + "lastModifiedBy").text or "", "")
        self.assertEqual(core.find(CP + "revision").text, "1")
        self.assertIsNone(core.find(CP + "lastPrinted"))
        created = core.find("{http://purl.org/dc/terms/}created").text
        modified = core.find("{http://purl.org/dc/terms/}modified").text
        self.assertEqual(created, modified)
        year = datetime.datetime.now(datetime.timezone.utc).year
        self.assertTrue(created.startswith(str(year)), created)

    # ---------------------------------------------------------------- 落点

    def test_default_out_is_under_temp_and_existing_out_is_refused(self):
        md = self.dir / "稿.md"
        md.write_text(fixture("印章备案.md"), encoding="utf-8")
        r = support.run(support.CONVERTER, md, "--template", template("1-2."))
        self.assertEqual(r.code, 0, r)
        path = pathlib.Path(r.out.splitlines()[0].split("已写出 ", 1)[1].strip())
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent, pathlib.Path(tempfile.gettempdir()) / "to-docx")
        self.assertTrue(path.name.startswith("稿-"))
        before = path.read_bytes()
        r2 = support.run(support.CONVERTER, md, "--template", template("1-2."), "--out", path)
        self.assertEqual(r2.code, 1)
        self.assertIn("不覆盖", r2.err)
        self.assertEqual(path.read_bytes(), before)

    def test_missing_inputs(self):
        r = support.run(support.CONVERTER, self.dir / "没有.md", "--template", template("1-2."), "--out", self.out)
        self.assertEqual(r.code, 1)
        self.assertIn("稿子不存在", r.err)
        md = self.dir / "稿.md"
        md.write_text("# 题\n", encoding="utf-8")
        r = support.run(support.CONVERTER, md, "--template", self.dir / "没有.docx", "--out", self.out)
        self.assertEqual(r.code, 1)
        self.assertIn("模板不存在", r.err)
        r = support.run(support.CONVERTER, md, "--out", self.out)
        self.assertEqual(r.code, 2)


if __name__ == "__main__":
    unittest.main()
