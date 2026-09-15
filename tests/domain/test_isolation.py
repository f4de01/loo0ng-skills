"""两个 CLI 的依赖边界与本 skill 的会话边界（#29、#16 验收）。

运行：python -m unittest tests/domain/test_isolation.py

- 依赖：`preset.py` 与 `sketch.py` 只 import 标准库，不 import 图引擎或别的兄弟脚本；写图只经引擎子进程。
- 判重：相似度那一半随 ADR-0024 从脚本里删干净（没有 difflib、没有阈值、没有「待定」）。
- 退场：活图、出厂种子、入库、回流、docx-text 随 ADR-0023 退场，本 skill 一处不留。
- 会话：导入只在开发会话里做，正文要写明律师不可导入；另存那一问未拍板不落。
"""
import ast
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
DOMAIN = REPO / "skills" / "engineering" / "domain"
SCRIPTS = [DOMAIN / "scripts" / "sketch.py", DOMAIN / "scripts" / "preset.py"]
正文 = DOMAIN / "SKILL.md"
# ADR-0023 退场的词：活图与出厂种子那套两份图、入库、回流，以及搬去 to-docx 的 docx-text。
退场的词 = ("活图", "出厂种子", "入库", "intake", "回流", "from-case", "docx-text", "领域图", "领域目录")


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").partition(".")[0])
    return names


class 依赖(unittest.TestCase):
    def test_只用标准库(self):
        for script in SCRIPTS:
            mods = imported_modules(script)
            self.assertTrue(mods, "%s 竟然没有 import" % script.name)
            for m in mods:
                self.assertIn(m, sys.stdlib_module_names, "%s 引用了非标准库模块 %s" % (script.name, m))

    def test_不import引擎与兄弟脚本(self):
        for script in SCRIPTS:
            mods = imported_modules(script)
            for f in ("graph", "archive", "fill", "sketch", "preset", "loo0ng"):
                self.assertNotIn(f, mods, "%s import 了 %s（跨 skill 一律子进程互调）" % (script.name, f))

    def test_不带BOM(self):
        for script in SCRIPTS + [正文]:
            self.assertFalse(script.read_bytes().startswith(b"\xef\xbb\xbf"), script.name)


class 判重只剩同名(unittest.TestCase):
    """ADR-0024：同名判重是集合成员，留代码；像不像是判断，归模型加正文里的方法。"""

    def test_脚本里没有相似度(self):
        text = (DOMAIN / "scripts" / "sketch.py").read_text(encoding="utf-8")
        for 印记 in ("difflib", "SequenceMatcher", "ratio", "0.75", "STATUS_PENDING", "as-new", "as_new"):
            self.assertNotIn(印记, text, "相似判重从脚本里删干净：还留着 %r" % 印记)
        self.assertNotIn("「待定」", text.replace("没有「待定」", ""), "「待定」不再是一个状态")

    def test_正文把相似判给模型(self):
        text = 正文.read_text(encoding="utf-8")
        self.assertIn("相似不同名由你判，脚本不判", text)
        self.assertIn("图里现有的标题", text, "判相似靠 check 末尾那份清单")


class 退场(unittest.TestCase):
    def test_本skill一处不提退场的那几样(self):
        for p in sorted(DOMAIN.rglob("*.md")) + SCRIPTS:
            text = p.read_text(encoding="utf-8")
            for 词 in 退场的词:
                self.assertNotIn(词, text, "%s 还提着退场的「%s」（ADR-0023）" % (p.name, 词))

    def test_回流那份references删了(self):
        self.assertFalse((DOMAIN / "references" / "回流.md").exists())
        self.assertEqual(sorted(p.name for p in (DOMAIN / "references").iterdir()),
                         ["时限句.md", "雏形格式.md"])


class 会话边界(unittest.TestCase):
    def test_导入只在开发会话且律师不可用(self):
        text = 正文.read_text(encoding="utf-8")
        self.assertIn("只在开发会话里做，律师不可导入", text)
        self.assertIn("第二双眼", text, "导入的产物进仓库那次 diff 要经第二双眼（硬边界 2）")

    def test_另存未拍板不落(self):
        text = 正文.read_text(encoding="utf-8")
        self.assertIn("未拍板不另存", text)
        self.assertIn("去案件化", text, "标题改法先回显、律师一句话之后才落")

    def test_起手不跑雏形(self):
        self.assertIn("起手不跑雏形", 正文.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
