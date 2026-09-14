"""起手 CLI 的依赖边界（#31 验收）：import 只含标准库，不 import 图引擎，写图只经引擎子进程。

运行：python -m unittest tests/loo0ng-setup-case/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "productivity" / "loo0ng-setup-case"
SCRIPT = SKILL / "scripts" / "setup.py"


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").partition(".")[0])
    return names


class IsolationTest(unittest.TestCase):
    def test_only_standard_library(self):
        mods = imported_modules(SCRIPT)
        self.assertTrue(mods, "setup.py 竟然没有 import")
        for m in mods:
            self.assertIn(m, sys.stdlib_module_names, "setup.py 引用了非标准库模块 %s" % m)

    def test_does_not_import_engine_or_siblings(self):
        mods = imported_modules(SCRIPT)
        for f in ("graph", "archive", "statement", "sketch", "md2docx", "gate", "loo0ng"):
            self.assertNotIn(f, mods, "setup.py import 了 %s" % f)

    def test_no_bom(self):
        for path in (SCRIPT, SKILL / "SKILL.md", *(SKILL / "references").iterdir()):
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), "%s 带 BOM" % path.name)


class SeedTemplateTest(unittest.TestCase):
    """种子模板住在本 skill 目录里（ADR-0009），之后没有任何 skill 往工作区的 AGENTS.md 里写。"""

    def test_工作区指针块模板四项齐全(self):
        text = (SKILL / "references" / "工作区AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("{领域}", text)
        self.assertIn("{领域目录}", text)
        for expected in ("图.json", "图视图.md", "图视图.json",
                        "loo0ng-setup-case", "loo0ng-doit", "ask-loo0ng", "只读"):
            self.assertIn(expected, text, "指针块模板里缺 %s" % expected)

    def test_既有成品审查报告模板五段固定(self):
        text = (SKILL / "references" / "既有成品审查报告.md").read_text(encoding="utf-8")
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, ["## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"],
                         "审查报告五段固定、顺序固定（loo0ng-to-docx/references/审查报告.md）")


if __name__ == "__main__":
    unittest.main()
