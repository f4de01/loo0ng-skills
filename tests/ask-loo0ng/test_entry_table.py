"""路由自持的入口表（#33 验收，ADR-0005）：表里三个入口与实际的 skill 一致，双旗齐全。

改任何入口必改这张表是 `AGENTS.md` 的结构不变量；这里把它变成会红的断言。
运行：python -m unittest tests/ask-loo0ng/test_入口表.py
"""
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "skills" / "in-progress" / "ask-loo0ng"
SKILL = SKILL_DIR / "SKILL.md"
YAML = SKILL_DIR / "agents" / "openai.yaml"
# 律师面对的三个入口：两个编排 skill 加路由本身（ADR-0005、ADR-0008、ADR-0010）。
入口 = ("setup-case", "doit", "ask-loo0ng")
显示名 = {"setup-case": "起手", "doit": "办节点", "ask-loo0ng": "问路"}


def 正文():
    return SKILL.read_text(encoding="utf-8")


def 表里的行():
    """入口表是正文里唯一一张四列表，第一列是反引号包着的入口名。"""
    rows = {}
    for line in 正文().splitlines():
        m = re.match(r"^\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


class 入口表Test(unittest.TestCase):
    def test_表里恰好这三个入口(self):
        self.assertEqual(sorted(入口), sorted(表里的行()), "入口表与三个入口对不上")

    def test_每个入口的名字都真有这件skill(self):
        for name in 表里的行():
            skill = REPO / "skills" / "in-progress" / name / "SKILL.md"
            self.assertTrue(skill.is_file(), "入口表指向不存在的 skill：%s" % name)
            front = skill.read_text(encoding="utf-8")
            self.assertIn('name: %s\n' % name, front, "%s 的 frontmatter name 与目录名不一致" % name)

    def test_显示名是中文且与工作区指针块一致(self):
        指针块 = (REPO / "skills" / "in-progress" / "setup-case" / "references" / "工作区AGENTS.md").read_text(encoding="utf-8")
        for name, 名 in 表里的行().items():
            self.assertEqual(显示名[name], 名, "%s 的显示名变了" % name)
            self.assertIn("%s（%s）" % (name, 名), 指针块, "%s 的显示名与工作区指针块对不上" % name)

    def test_登记进了桶README(self):
        # 改造期七件都在 in-progress/，非 promoted：只登记在桶 README，不进 plugin.json 与根 README（ADR-0022）
        bucket_readme = (REPO / "skills" / "in-progress" / "README.md").read_text(encoding="utf-8")
        self.assertIn("[ask-loo0ng](./ask-loo0ng/SKILL.md)", bucket_readme)


class 双旗Test(unittest.TestCase):
    def test_SKILL_md带旗(self):
        self.assertIn("disable-model-invocation: true", 正文())

    def test_openai_yaml带旗(self):
        self.assertIn("allow_implicit_invocation: false", YAML.read_text(encoding="utf-8"))

    def test_不带BOM(self):
        for p in (SKILL, YAML):
            self.assertFalse(p.read_bytes().startswith(b"\xef\xbb\xbf"), "%s 带 BOM" % p.name)


class 打法Test(unittest.TestCase):
    """`$` 提及打裸名，不带命名空间前缀（开发者 2026-09-07 拍板，见 #33 评论）。"""

    def test_美元符号后面只跟裸名(self):
        for 名 in re.findall(r"\$([A-Za-z0-9:<>_-]+)", 正文()):
            if 名.startswith("<"):  # 样例里的 $<插件名>:doit 正是反面教材，正文写明「不是」
                continue
            self.assertIn(名, 入口, "`$%s` 不是裸的入口名" % 名)

    def test_反面教材那一句还在(self):
        self.assertIn("不带命名空间前缀", 正文(), "裸名这条裁定的正文说明没了")


class 不写图Test(unittest.TestCase):
    def test_正文写明只读(self):
        t = 正文()
        for 句 in ("不触发", "不写图", "一个字节都不变"):
            self.assertIn(句, t, "正文缺「%s」" % 句)

    def test_正文写明入口都存在与以对方SKILL为准(self):
        t = 正文()
        self.assertIn("即使它们不在你看到的 skill 列表里", t)
        self.assertRegex(t, r"以.{0,10}`SKILL\.md`.{0,10}为准")


if __name__ == "__main__":
    unittest.main()
