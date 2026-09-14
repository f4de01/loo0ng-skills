"""路由取领域图路径的全链（#92 验收，ADR-0019）：每一步都经工作区 AGENTS.md，不自己拼包内的路径。

领域目录搬出 skill 包之后（ADR-0019），律师的领域图住包外的活图，包内 assets/ 降为出厂种子。
**核下来路由这一侧是零改动**：正文里领域图出现的四处都不自己给路径：

    定位段（「我怎么答三问」开头）  路径从工作区根的 AGENTS.md 取，是起手落下的
    五问树的问 3 与问 4            只说「领域图」，不提它在哪
    查时限那一步                   同一条路径，读不到只有按 AGENTS.md 试过才算数

上游 #90 把 AGENTS.md 那一行改成指活图之后，路由跟着就读活图了，一个字不用改。这份单测把
「零改动」变成会红的断言：哪天有人在这四处任何一处写死一条包内路径，或者把领域图说成随
skill 包分发的那一份，这里红。

活图上的行为（真去打开那份活图、把只住活图的时限句原样附上）由 eval 用例「活图多一件」覆盖。
运行：python -m unittest tests/ask-loo0ng/test_live_domain.py
"""
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "skills" / "in-progress" / "ask-loo0ng"
SKILL = SKILL_DIR / "SKILL.md"
正文文件 = (SKILL, SKILL_DIR / "references" / "下一任务.md")
# 包内路径的几种写法。路由一处都不该出现：它拿到的路径只有 AGENTS.md 那一行给的。
包内路径 = ("assets/", "assets\\", "domain/scripts", "~/.loo0ng")
# 「领域图随包分发」这类措辞：ADR-0019 之后它是错的，包内那份是出厂种子，律师读的是活图。
过时措辞 = ("领域图随 skill 包", "领域图随包", "skill 包内置的领域图", "领域图内置在 skill 包")


def 读(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def 那一行(标记: str) -> str:
    行 = [l for l in 读(SKILL).splitlines() if 标记 in l]
    assert len(行) == 1, "正文里带「%s」的那一行不见了或多出一行：%d 行" % (标记, len(行))
    return 行[0]


class 路径来源Test(unittest.TestCase):
    def test_正文不写死包内路径(self):
        for p in 正文文件:
            文 = 读(p)
            for 片 in 包内路径:
                self.assertNotIn(片, 文, "%s 里写死了包内路径「%s」：领域图路径只能从工作区 "
                                         "AGENTS.md 那一行取（ADR-0019）" % (p.name, 片))

    def test_正文没有领域图随包分发的措辞(self):
        for p in 正文文件:
            文 = 读(p)
            for 片 in 过时措辞:
                self.assertNotIn(片, 文, "%s 里还写着「%s」：包内那份是出厂种子，"
                                         "律师读的是包外的活图（ADR-0019）" % (p.name, 片))

    def test_定位段取路径这一步点名AGENTS_md(self):
        """四处的第一处：先读案件图，再打开领域图，路径在工作区根的 AGENTS.md 里。"""
        self.assertIn("AGENTS.md", 那一行("再打开领域图"),
                      "定位段没写明领域图的路径从工作区 AGENTS.md 取")

    def test_五问树的问3问4不自己给路径(self):
        """四处的第二、三处：决策树只说「领域图」，路径这件事整段不碰，才不会绕开 AGENTS.md。"""
        for 标记 in ("最近动过的那个节点所在的模块", "回头补空"):
            行 = 那一行(标记)
            self.assertIn("领域图", 行)
            for 片 in ("AGENTS.md", "assets", "领域目录", "路径"):
                self.assertNotIn(片, 行, "五问树那一行（%s）自己讲起了领域图在哪：路径只有定位段"
                                         "与查时限那一步说，且都指向 AGENTS.md" % 标记)

    def test_查时限那一步也只认AGENTS_md给的路径(self):
        """四处的第四处：读不到只有真按 AGENTS.md 里的路径试过才算数（#71 写硬的那条）。"""
        self.assertIn("真去 `AGENTS.md` 取了路径", 读(SKILL),
                      "「读不到」只有按 AGENTS.md 里的路径试过才算数，这一句没了（#71、#92）")
