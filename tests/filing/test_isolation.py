"""归档 CLI 的依赖边界：import 只含标准库，不引用图引擎，也不引用别的 skill 的脚本。

运行：python -m unittest discover -s tests/filing -p 'test_*.py'
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "skills" / "in-progress" / "filing" / "scripts"
CLIS = ("archive.py",)


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
    def test_scripts_dir_holds_only_the_archive_cli(self):
        self.assertEqual(sorted(p.name for p in SCRIPTS.glob("*.py")), sorted(CLIS),
                         "filing 只有一个 CLI：陈述落档随 ADR-0023 退场")

    def test_only_standard_library(self):
        for name in CLIS:
            mods = imported_modules(SCRIPTS / name)
            self.assertTrue(mods, "%s 竟然没有 import" % name)
            for m in mods:
                self.assertIn(m, sys.stdlib_module_names, "%s 引用了非标准库模块 %s" % (name, m))

    def test_no_cross_reference(self):
        forbidden = ("archive", "graph", "loo0ng", "fill", "sketch", "setup")
        for name in CLIS:
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            mods = imported_modules(SCRIPTS / name)
            for f in forbidden:
                self.assertNotIn(f, mods, "%s import 了 %s" % (name, f))
            self.assertNotIn("graph.py", text, "%s 不该指向引擎脚本" % name)


if __name__ == "__main__":
    unittest.main()
