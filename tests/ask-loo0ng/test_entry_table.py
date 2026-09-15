"""路由自持的两张表（#19 验收，ADR-0005、ADR-0023）：表里七件与实际的 skill 一致，双旗对得上。

入口表管律师打名字的三件，「说一句话就到」那张管其余四件；改任一件的名字、触发词或职责都要
改这两张表（`AGENTS.md` 的结构不变量 2）。这里把它变成会红的断言。
运行：python -m unittest tests/ask-loo0ng/test_entry_table.py
"""
import re
import unittest

from support import SKILL, YAML, 下一任务, 件, 全部skill名, 正文, 表里的行

# 律师打名字的三件：两个编排 skill 加路由本身（ADR-0005、ADR-0008、ADR-0010）。
入口 = ("setup-case", "doit", "ask-loo0ng")
# 说一句话就到的四件：模型自行调用，不带双旗（结构不变量 3）。
一句话 = ("filing", "graph", "domain", "to-docx")
显示名 = {"setup-case": "起手", "doit": "办节点", "ask-loo0ng": "问路"}
入口表标题 = "## 入口表"
一句话表标题 = "### 另外四件：说一句话就到"


class 两张表Test(unittest.TestCase):
    def test_入口表恰好这三个入口(self):
        self.assertEqual(sorted(入口), sorted(表里的行(入口表标题)), "入口表与三个入口对不上")

    def test_另一张表恰好其余四件(self):
        self.assertEqual(sorted(一句话), sorted(表里的行(一句话表标题)), "说一句话那张表与四件参考 skill 对不上")

    def test_两张表合起来就是仓库里的七件(self):
        self.assertEqual(全部skill名(), sorted(入口 + 一句话), "skills/ 下实有的 skill 与两张表对不上")

    def test_每个名字都真有这件skill(self):
        for name in list(表里的行(入口表标题)) + list(表里的行(一句话表标题)):
            skill = 件(name) / "SKILL.md"
            self.assertTrue(skill.is_file(), "表里指向不存在的 skill：%s" % name)
            front = skill.read_text(encoding="utf-8")
            self.assertIn('name: %s\n' % name, front, "%s 的 frontmatter name 与目录名不一致" % name)

    def test_显示名是中文且与工作区指针块一致(self):
        指针块 = (件("setup-case") / "references" / "工作区AGENTS.md").read_text(encoding="utf-8")
        for name, 名 in 表里的行(入口表标题).items():
            self.assertEqual(显示名[name], 名, "%s 的显示名变了" % name)
            self.assertIn("%s（%s）" % (name, 名), 指针块, "%s 的显示名与工作区指针块对不上" % name)

    def test_登记进了桶README(self):
        # 改造期七件都在 in-progress/，非 promoted：只登记在桶 README，不进 plugin.json 与根 README（ADR-0022）
        bucket_readme = (件("ask-loo0ng").parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("[ask-loo0ng](./ask-loo0ng/SKILL.md)", bucket_readme)


class 双旗Test(unittest.TestCase):
    def test_路由自己带双旗(self):
        self.assertIn("disable-model-invocation: true", 正文())
        self.assertIn("allow_implicit_invocation: false", YAML.read_text(encoding="utf-8"))

    def test_入口表里的三件都带双旗(self):
        for name in 表里的行(入口表标题):
            self.assertIn("disable-model-invocation: true", (件(name) / "SKILL.md").read_text(encoding="utf-8"),
                          "%s 在入口表里，却不是编排 skill" % name)

    def test_另一张表里的四件都不带旗(self):
        for name in 表里的行(一句话表标题):
            self.assertNotIn("disable-model-invocation", (件(name) / "SKILL.md").read_text(encoding="utf-8"),
                             "%s 带着编排旗，不该在「说一句话就到」那张表里" % name)

    def test_不带BOM(self):
        for p in (SKILL, YAML):
            self.assertFalse(p.read_bytes().startswith(b"\xef\xbb\xbf"), "%s 带 BOM" % p.name)


class 打法Test(unittest.TestCase):
    """`$` 提及打裸名，不带命名空间前缀（开发者 2026-09-07 拍板，见旧仓库 #33 评论）。"""

    def test_美元符号后面只跟裸名(self):
        for 名 in re.findall(r"\$([A-Za-z0-9:<>_-]+)", 正文()):
            if 名.startswith("<"):  # 样例里的 $<插件名>:doit 正是反面教材，正文写明「不是」
                continue
            self.assertIn(名, 入口, "`$%s` 不是裸的入口名" % 名)

    def test_反面教材那一句还在(self):
        self.assertIn("不带命名空间前缀", 正文(), "裸名这条裁定的正文说明没了")


class 退场的能力Test(unittest.TestCase):
    """ADR-0023、ADR-0024 之后这几样东西不存在了，地图上一个字都不该提（#19 验收 1）。"""

    退场 = ("回流", "陈述", "活图", "领域图", "出厂种子", "入库", "门禁", "领域目录")

    def test_两处正文都不提(self):
        for p in (SKILL, 下一任务):
            文 = p.read_text(encoding="utf-8")
            for 词 in self.退场:
                self.assertNotIn(词, 文, "%s 里还提着退场的「%s」（ADR-0023、ADR-0024）" % (p.name, 词))

    def test_description也不提(self):
        头 = 正文().split("---")[1]
        for 词 in self.退场:
            self.assertNotIn(词, 头, "frontmatter 的 description 里还提着「%s」" % 词)


if __name__ == "__main__":
    unittest.main()
