"""两个 CLI 的依赖边界（#28 验收）：互不 import；转换器只依赖 python-docx，门禁本体零第三方依赖、
PyMuPDF 只在渲染分支里 import。

运行：python -m unittest tests/to-docx/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "skills" / "productivity" / "to-docx" / "scripts"
ALLOWED = {"md2docx.py": {"docx"}, "gate.py": {"pymupdf"}}
# 模块顶层许出现的第三方 import。门禁这一格是空的：没装 PyMuPDF 的机器上，顶层 import 会让连静态检查
# 都起不来，而主力环境恒定没有渲染器（#57、ADR-0017）。
TOP_LEVEL_ALLOWED = {"md2docx.py": {"docx"}, "gate.py": set()}


def imported_modules(path, top_level_only=False):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in (tree.body if top_level_only else ast.walk(tree)):
        if isinstance(node, ast.Import):
            names.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").partition(".")[0])
    return names


class IsolationTest(unittest.TestCase):
    def test_third_party_imports_are_exactly_the_declared_ones(self):
        for name, allowed in ALLOWED.items():
            mods = imported_modules(SCRIPTS / name)
            third = {m for m in mods if m not in sys.stdlib_module_names}
            self.assertEqual(third, allowed, "%s 的第三方 import 应只有 %s，实际 %s" % (name, allowed, third))

    def test_gate_imports_pymupdf_only_inside_the_render_branch(self):
        for name, allowed in TOP_LEVEL_ALLOWED.items():
            top = imported_modules(SCRIPTS / name, top_level_only=True)
            third = {m for m in top if m not in sys.stdlib_module_names}
            self.assertEqual(third, allowed,
                             "%s 的模块顶层第三方 import 应只有 %s，实际 %s" % (name, allowed, third))

    def test_no_cross_reference(self):
        for name in ALLOWED:
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            mods = imported_modules(SCRIPTS / name)
            for other in ALLOWED:
                if other != name:
                    self.assertNotIn(other[:-3], mods, "%s import 了 %s" % (name, other))
                    self.assertNotIn(other, text, "%s 不该提到 %s" % (name, other))
            for f in ("graph", "archive", "statement", "loo0ng"):
                self.assertNotIn(f, mods, "%s import 了 %s" % (name, f))

    def test_gate_drives_word_only_through_powershell(self):
        text = (SCRIPTS / "gate.py").read_text(encoding="utf-8")
        self.assertIn("powershell", text)
        self.assertNotIn("win32com", text)
        self.assertNotIn("pythoncom", text)


if __name__ == "__main__":
    unittest.main()
