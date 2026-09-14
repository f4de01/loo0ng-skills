"""19 件官方模板回归：每件各出一份甲乙丙占位件，全部通过门禁；4 件含合并单元格的模板与模板同形。

运行：python -m unittest tests/to-docx/test_templates.py

两条跑道（ADR-0017）：默认跑道无渲染，只用门禁本体（推算层），零第三方依赖、19 件几秒钟跑完、任何机器上
必须全绿、不许 skip；`TemplatesRegressionRendered` 把同一批接上渲染层再跑一遍（每件起一次 Word，19 件约两三
分钟；Codex 的 30 秒 shell 超时装不下），拿不到渲染通道时整类 skip 并打印一行说明。
"""
import pathlib
import shutil
import tempfile
import unittest

import support
from support import W, all_templates, body_blocks, convert, gate, read_xml, table_signature, template

MERGED = ("1-1.", "3-1.", "3-2.", "8-2.")


class TemplatesRegression(unittest.TestCase):
    EXTRA = ("--no-render",)  # 子类置空即接上渲染层

    def setUp(self):
        if not self.EXTRA:
            support.require_render(self)
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-tpl-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_every_template_yields_a_placeholder_docx_that_passes_the_gate(self):
        failures = []
        for tpl in all_templates():
            out = self.dir / (tpl.stem[:6] + ".docx")
            r = convert(support.markdown_mirroring(tpl), tpl, out)
            if r.code != 0:
                failures.append("%s：转换 %r" % (tpl.name, r))
                continue
            g = gate(out, "--template", tpl, *self.EXTRA)
            if g.code != 0:
                failures.append("%s：门禁退出码 %d %s %s %s"
                                % (tpl.name, g.code, g.result and g.result["不通过项"],
                                   g.result and g.result["需人眼项"], g.err.strip()))
        self.assertEqual(failures, [], "\n".join(failures))


class TemplatesShape(unittest.TestCase):
    """不跑门禁的两件，只看模板与转换器：不分跑道，也就不该被渲染层的 skip 波及。"""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-tpl-shape-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_there_are_nineteen_templates(self):
        self.assertEqual(len(all_templates()), 19)

    def test_merged_cell_templates_keep_their_shape(self):
        for prefix in MERGED:
            tpl = template(prefix)
            out = self.dir / (prefix + "docx")
            r = convert(support.markdown_mirroring(tpl), tpl, out)
            self.assertEqual(r.code, 0, r)
            tpl_tables = read_xml(tpl).find(W + "body").findall(W + "tbl")
            out_tables = [b for b in body_blocks(out) if b.tag == W + "tbl"]
            merged = any(cell[0] != "1" or cell[1] is not None
                         for t in tpl_tables for _, cells in table_signature(t)[1] for cell in cells)
            self.assertTrue(merged, "%s 应含合并单元格" % prefix)
            self.assertEqual([table_signature(t) for t in out_tables], [table_signature(t) for t in tpl_tables], prefix)


class TemplatesRegressionRendered(TemplatesRegression):
    """同一批 19 件接上渲染层再跑一遍。缺渲染通道时整类 skip 并打印说明（ADR-0017）。"""
    EXTRA = ()


if __name__ == "__main__":
    unittest.main()
