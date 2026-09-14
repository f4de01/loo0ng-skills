"""19 件官方模板逐件回归：每件跑「只留黄」与「全填」两遍，比表格几何与 run 格式，再各跑一次门禁。

运行：python -m unittest tests/to-docx/test_templates.py

这是填模板差量路线的主验收（ADR-0023，#13）。两遍是出件的两个极端：一个字都没填（全篇留黄）与每个槽都
填了（一处黄都不剩）。两遍都要满足：

  - 表格几何（tblPr / tblGrid / 每行 trPr / 每格 tcPr 的 XML）逐字节不变；
  - 槽外每个字符的 run 格式（rPr 去掉 highlight）不变，固定文字与槽混在一段的那些段落正是这条要守的；
  - 只留黄那一遍：每个槽都落在高亮里，文字一个字不变；
  - 门禁不给不通过（需人眼是允许的：这台机器没有渲染器，空白页那一项常落在带内，ADR-0017）。

两条跑道（ADR-0017）：默认跑道无渲染，只用门禁本体（推算层），零第三方依赖、任何机器上必须全绿、不许
skip；`TemplatesRegressionRendered` 把同一批接上渲染层再跑一遍（每件起一次 Word，19 件约两三分钟；Codex
的 30 秒 shell 装不下），拿不到渲染通道时整类 skip 并打印一行说明。
"""
import pathlib
import shutil
import tempfile
import unittest

import support
from support import W, all_templates, apply, fill_all_ops, gate, read_xml, table_signature, template, 填

MERGED = ("1-1.", "3-1.", "3-2.", "8-2.")
填的字 = "某某"


def 槽外格式(before, after, 文本, 填了) -> str:
    """槽外每个字符的格式在填前填后是不是同一串；不同就回一句人话，同就回空串。

    填了槽的段落长度会变，所以按槽的边界分段对齐：槽之间那几截逐字符比，槽本身跳过。
    """
    for idx, 旧 in before[1].items():
        新 = after[1].get(idx)
        if 新 is None:
            return "p%d 整段没了" % idx
        if not 填了:
            if 旧 != 新:
                return "p%d 的字符格式变了" % idx
            continue
        pos0 = pos1 = 0
        for m in 填.PLACEHOLDER.finditer(文本[idx]):
            s, e = m.start(), m.end()
            if 旧[pos0:s] != 新[pos1:pos1 + (s - pos0)]:
                return "p%d 槽前那一截的格式变了" % idx
            pos1 += (s - pos0) + len(填的字)
            pos0 = e
        if 旧[pos0:] != 新[pos1:]:
            return "p%d 段尾的格式变了" % idx
    return ""


class TemplatesRegression(unittest.TestCase):
    EXTRA = ("--no-render",)  # 子类置空即接上渲染层

    def setUp(self):
        if not self.EXTRA:
            support.require_render(self)
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-tpl-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_every_template_survives_both_passes_with_its_geometry_intact(self):
        failures = []
        for tpl in all_templates():
            doc = support.Document(str(tpl))
            文本 = [填.text_of(p) for p in 填.paragraphs(doc)]
            before = support.geometry_snapshot(tpl)
            for 遍, ops in (("只留黄", []), ("全填", fill_all_ops(tpl, 填的字))):
                out = self.dir / ("%s-%s.docx" % (tpl.stem[:6], 遍))
                r = apply(tpl, ops, out)
                if r.code != 0:
                    failures.append("%s %s：施加 %r" % (tpl.name, 遍, r))
                    continue
                after = support.geometry_snapshot(out)
                if before[0] != after[0]:
                    failures.append("%s %s：表格几何变了" % (tpl.name, 遍))
                bad = 槽外格式(before, after, 文本, 遍 == "全填")
                if bad:
                    failures.append("%s %s：%s" % (tpl.name, 遍, bad))
                failures += self.check_slots(tpl, out, 遍, 文本)
                failures += self.check_gate(tpl, out, 遍, len(文本))
        self.assertEqual(failures, [], "\n".join(failures))

    def check_gate(self, tpl, out, 遍, 段数):
        """门禁跑得过这件吗。

        只留黄那一遍是**真的出件形状**（一个槽都填不上时交出去的就是它），整件结论不许是不通过。
        全填那一遍是合成的极端：每个槽都塞同一串「某某」，篇幅与分页跟着变，6-2 的末页会空出来，那是
        塞进去的字的事，不是施加机制的事。所以那一遍只断这条路自己管的两项（改动段残留占位、元数据残留）
        不出现，几何项交给出件时的真门禁。
        """
        changed = ",".join(str(i) for i in range(段数))
        g = gate(out, "--template", tpl, "--changed", changed, *self.EXTRA)
        if g.result is None:
            return ["%s %s：门禁跑不动 %s %s" % (tpl.name, 遍, g.code, g.err.strip())]
        if 遍 == "只留黄":
            if g.result["结论"] == "不通过":
                return ["%s 只留黄：门禁不通过 %s" % (tpl.name, g.result["不通过项"])]
            return []
        ours = [x for x in g.result["不通过项"] if x.startswith(("改动段", "元数据残留"))]
        return ["%s 全填：%s" % (tpl.name, ours)] if ours else []

    def check_slots(self, tpl, out, 遍, 文本):
        """只留黄：文字一个字不变、每个槽都在高亮里；全填：一个槽都不剩。"""
        bad = []
        doc = support.Document(str(out))
        for idx, p in enumerate(填.paragraphs(doc)):
            hl = 填.highlight_ranges(p)
            sl = 填.slots(p)
            if 遍 == "全填":
                if sl:
                    bad.append("%s 全填：p%d 还剩 %d 个槽" % (tpl.name, idx, len(sl)))
                continue
            if 填.text_of(p) != 文本[idx]:
                bad.append("%s 只留黄：p%d 的文字被动过" % (tpl.name, idx))
            for s, e, 原文 in sl:
                if not any(a <= s and e <= b for a, b in hl):
                    bad.append("%s 只留黄：p%d 的槽「%s」没留黄" % (tpl.name, idx, 原文))
        return bad


class TemplatesShape(unittest.TestCase):
    """不跑门禁的几件，只看模板与施加：不分跑道，也就不该被渲染层的 skip 波及。"""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-tpl-shape-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_there_are_nineteen_templates(self):
        self.assertEqual(len(all_templates()), 19)

    def test_every_template_has_slots_to_fill(self):
        for tpl in all_templates():
            with self.subTest(模板=tpl.name):
                self.assertTrue(support.slots_of(tpl), "一个槽都认不出来，清单就没什么可读的")

    def test_merged_cell_templates_keep_their_shape(self):
        for prefix in MERGED:
            tpl = template(prefix)
            out = self.dir / (prefix + "docx")
            r = apply(tpl, fill_all_ops(tpl, 填的字), out)
            self.assertEqual(r.code, 0, r)
            tpl_tables = read_xml(tpl).find(W + "body").findall(W + "tbl")
            out_tables = read_xml(out).find(W + "body").findall(W + "tbl")
            merged = any(cell[0] != "1" or cell[1] is not None
                         for t in tpl_tables for _, cells in table_signature(t)[1] for cell in cells)
            self.assertTrue(merged, "%s 应含合并单元格" % prefix)
            self.assertEqual([table_signature(t) for t in out_tables], [table_signature(t) for t in tpl_tables], prefix)

    def test_the_templates_own_highlights_are_still_there_after_a_full_fill(self):
        """19 件里有 24 处模板自带的黄，标的是条件块与提示句：填完槽它们照样在，等模型显式去黄或律师动手。"""
        tpl = template("4-1.")
        亮 = sum(len(填.highlight_ranges(p)) for p in 填.paragraphs(support.Document(str(tpl))))
        self.assertTrue(亮, "4-1 本来就带黄，这条断言才站得住")
        out = self.dir / "自带黄.docx"
        self.assertEqual(apply(tpl, fill_all_ops(tpl, 填的字), out).code, 0)
        doc = support.Document(str(out))
        self.assertTrue(sum(len(填.highlight_ranges(p)) for p in 填.paragraphs(doc)), "自带的黄被吃掉了")


class TemplatesRegressionRendered(TemplatesRegression):
    """同一批 19 件接上渲染层再跑一遍。缺渲染通道时整类 skip 并打印说明（ADR-0017）。"""
    EXTRA = ()


if __name__ == "__main__":
    unittest.main()
