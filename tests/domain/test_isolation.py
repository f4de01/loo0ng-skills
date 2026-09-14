"""雏形 CLI 的依赖边界（#29 验收）：import 只含标准库，不 import 图引擎，写入只经引擎子进程。
外加回流的会话边界（#34 验收，ADR-0012；#91 改口径，ADR-0019）：回流有两条路，
律师侧逐节点那条挂在办节点的确认之后，开发侧批量那条仍只在开发会话里，起手那一回合里没有这个动作。

运行：python -m unittest tests/domain/test_isolation.py
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "in-progress" / "domain" / "scripts" / "sketch.py"
# 律师面对的三个入口：两个编排 skill 加路由（ADR-0005、ADR-0008）。起手那一回合里没有回流这个动作；
# 办节点那件是律师侧逐节点回流的驱动者（ADR-0019），另按下面几条测；路由不再拿「回流」二字卡
# （ADR-0019 取代了 ADR-0012「路由不路由到回流」那一句），只测它没多长出第四个入口。
不提回流的入口 = ("setup-case",)
办节点 = REPO / "skills" / "in-progress" / "doit" / "SKILL.md"
路由 = REPO / "skills" / "in-progress" / "ask-loo0ng" / "SKILL.md"
# 开发侧批量那条路的印记：它们出现在办节点的正文里，就是把开发会话的活儿搬进了律师的回合。
# 「assets/」与「第二双眼」不在这张单子上：办节点提这两样都是为了拦（别往包内种子写、这条路没有第二双眼）。
开发侧印记 = ("from-case", "开分支", "npm run changeset", "--proposal")


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
        self.assertTrue(mods, "sketch.py 竟然没有 import")
        for m in mods:
            self.assertIn(m, sys.stdlib_module_names, "sketch.py 引用了非标准库模块 %s" % m)

    def test_does_not_import_engine_or_siblings(self):
        mods = imported_modules(SCRIPT)
        for f in ("graph", "archive", "statement", "md2docx", "gate", "loo0ng"):
            self.assertNotIn(f, mods, "sketch.py import 了 %s" % f)

    def test_no_bom(self):
        self.assertFalse(SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf"))


class 回流两条路(unittest.TestCase):
    """ADR-0019 取代了 ADR-0012 的会话那一条：律师侧逐节点在办节点的确认之后，开发侧批量仍只在开发会话。"""

    def test_起手的正文不提回流(self):
        found = [p for name in 不提回流的入口
                 for p in (REPO / "skills" / "in-progress" / name).rglob("*.md")
                 if "回流" in p.read_text(encoding="utf-8")]
        self.assertEqual([], found, "起手那一回合里没有回流这个动作：%s" % [str(p) for p in found])

    def test_路由没多长出第四个入口(self):
        """回流不是律师打得出来的入口：它是确认之后的一问，路由的入口表仍只有三行（ADR-0005）。"""
        表 = [行 for 行 in 路由.read_text(encoding="utf-8").splitlines()
              if 行.startswith("| `") and 行.count("|") >= 5]
        self.assertEqual(3, len(表), "入口表该只有三个入口：%s" % 表)
        for 名 in ("setup-case", "doit", "ask-loo0ng"):
            self.assertTrue(any("`%s`" % 名 in 行 for 行 in 表), "入口表缺 %s" % 名)

    def test_办节点正文里有律师侧那条路(self):
        text = 办节点.read_text(encoding="utf-8")
        self.assertIn("逐节点回流", text, "那一问挂在确认之后（ADR-0019），办节点的正文里要有它")
        self.assertIn("活图", text, "律师侧回流写的是活图，不是仓库里的出厂种子")
        self.assertIn("未拍板不写", text, "与雏形机制同一条规矩，正文里要写死")
        self.assertIn("没有第二双眼", text, "这条路为什么没有第二双眼，正文里要说清（#91 验收）")

    def test_办节点正文里没有开发侧那条路(self):
        text = 办节点.read_text(encoding="utf-8")
        for 印记 in 开发侧印记:
            self.assertNotIn(印记, text, "开发侧批量那条不在办案会话里做，正文不该出现 %r" % 印记)

    def test_两条路都写在领域skill的references里(self):
        step = (REPO / "skills" / "in-progress" / "domain" / "references" / "回流.md").read_text(encoding="utf-8")
        for 词 in ("回流", "律师侧", "开发侧", "活图", "出厂种子", "第二双眼"):
            self.assertIn(词, step, "回流的规矩住在 domain 的 references 里，缺 %r" % 词)


if __name__ == "__main__":
    unittest.main()
