"""起手 CLI 的依赖边界：import 只含标准库，不 import 兄弟 skill，写图只经引擎子进程。

运行：python -m unittest discover -s tests/setup-case -p 'test_isolation.py'
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "engineering" / "setup-case"
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
        for f in ("graph", "archive", "preset", "sketch", "fill", "loo0ng"):
            self.assertNotIn(f, mods, "setup.py import 了 %s" % f)

    def test_no_bom(self):
        for path in (SCRIPT, SKILL / "SKILL.md", *(SKILL / "references").iterdir()):
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), "%s 带 BOM" % path.name)


class PointerBlockTest(unittest.TestCase):
    """指针块模板住在本 skill 目录里（ADR-0009），之后没有任何 skill 往工作区的 AGENTS.md 里写。"""

    TEMPLATE = SKILL / "references" / "工作区AGENTS.md"

    def text(self):
        return self.TEMPLATE.read_text(encoding="utf-8")

    def test_四项齐全(self):
        text = self.text()
        self.assertIn("{预设图}", text)
        for expected in ("图.json", "图视图.md", "图视图.json",
                         "setup-case", "doit", "ask-loo0ng", "只读"):
            self.assertIn(expected, text, "指针块模板里缺 %s" % expected)

    def test_只有四项(self):
        项 = [line for line in self.text().splitlines() if line.startswith("- ")]
        self.assertEqual(len(项), 4, 项)

    def test_模板里没有领域目录那一行(self):
        """ADR-0023：只记预设图的名与归属，路径每次按名当场解析。"""
        text = self.text()
        for 旧 in ("{领域}", "{领域目录}", "领域目录"):
            self.assertNotIn(旧, text, "指针块模板里还有 %s" % 旧)


if __name__ == "__main__":
    unittest.main()
