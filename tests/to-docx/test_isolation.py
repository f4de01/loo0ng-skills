"""填模板 CLI 的依赖边界（#28 验收，#22 之后只剩它一个）：第三方 import 只有 python-docx，不 import 别的 skill。

运行：python -m unittest tests/to-docx/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "skills" / "productivity" / "to-docx" / "scripts"
ALLOWED = {"fill.py": {"docx"}}

# 3.9 上没有 `sys.stdlib_module_names`（3.10 才加），而这套测试也要在 3.9 解释器上跑得起来（#13）。
# 退路是这份明写的名单：脚本 import 的标准库就这些，新添一个标准库 import 就往这里加一行，
# 名单短反而把「第三方只有声明的那些」这条断言钉得更死。
STDLIB_FALLBACK = frozenset("""
argparse copy datetime importlib json os pathlib re secrets sys tempfile typing
""".split())


def stdlib_names():
    return set(getattr(sys, "stdlib_module_names", ())) or set(sys.builtin_module_names) | STDLIB_FALLBACK


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
    def test_the_scripts_dir_holds_exactly_the_declared_clis(self):
        self.assertEqual(sorted(p.name for p in SCRIPTS.glob("*.py")), sorted(ALLOWED),
                         "门禁整件退场（ADR-0024）之后 scripts/ 下只有 fill.py")

    def test_third_party_imports_are_exactly_the_declared_ones(self):
        for name, allowed in ALLOWED.items():
            mods = imported_modules(SCRIPTS / name)
            third = {m for m in mods if m not in stdlib_names()}
            self.assertEqual(third, allowed, "%s 的第三方 import 应只有 %s，实际 %s" % (name, allowed, third))

    def test_no_cross_reference(self):
        for name in ALLOWED:
            mods = imported_modules(SCRIPTS / name)
            for f in ("gate", "graph", "archive", "statement", "loo0ng"):
                self.assertNotIn(f, mods, "%s import 了 %s" % (name, f))


if __name__ == "__main__":
    unittest.main()
