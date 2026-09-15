"""skills/in-progress/setup-case/scripts/setup.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/setup-case -p 'test_*.py'

缝是起手 CLI 加临时工作区里的文件：每个测试在临时目录里调 main(argv)，再看目录形状、图、
两份视图、指针块与既有成品的登记条目落成了什么样。预设图由 #12 交的构造器（tests/共用/工作区.py）
用引擎自己造，领域是合成小领域「菜园」（ADR-0015）；个人预设图那一处靠环境变量 LOO0NG_HOME
换到临时目录，碰不到律师真的 ~/.loo0ng。文件名与内容全是合成的，没有案件内容。
"""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "in-progress" / "setup-case"
SCRIPT = SKILL / "scripts" / "setup.py"
PRESET_CLI = REPO / "skills" / "in-progress" / "domain" / "scripts" / "preset.py"
PERSONAL_HOME_ENV = "LOO0NG_HOME"   # 个人预设图的「家」，与 preset.py、eval 跑器同一个名字

sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

spec = importlib.util.spec_from_file_location("loo0ng_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

CELLS = ["待归档", "材料", "参考/模板", "参考/指南", "文书"]


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="setup-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = self.tmp / "案子"
        self.ws.mkdir()
        self.home = self.tmp / "家"
        old = os.environ.get(PERSONAL_HOME_ENV)
        os.environ[PERSONAL_HOME_ENV] = str(self.home)
        self.addCleanup(self.restore_home, old)

    @staticmethod
    def restore_home(old):
        if old is None:
            os.environ.pop(PERSONAL_HOME_ENV, None)
        else:
            os.environ[PERSONAL_HOME_ENV] = old

    def 造个人预设图(self, 名="菜园", 模块=None):
        return 工.造预设图(self.home / "预设图", 模块 if 模块 is not None else 工.菜园, 名=名)

    def cli(self, *argv, workspace=None):
        args = [str(a) for a in argv] + ["--workspace", str(workspace or self.ws)]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = setup.main(args)
            except SystemExit as e:  # argparse 的用法错
                code = e.code if isinstance(e.code, int) else 2
        return Run(code, out.getvalue(), err.getvalue())

    def 起手(self, *argv):
        self.造个人预设图()
        r = self.cli("init", "--preset", "菜园", "--owner", "个人", *argv)
        self.assertEqual(r.code, 0, r)
        return r

    def graph(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def view(self):
        return json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))

    def node(self, 标题):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == 标题:
                    return n
        raise AssertionError("图里没有节点「%s」" % 标题)

    def 指针块(self):
        return (self.ws / "AGENTS.md").read_text(encoding="utf-8")

    def 丢一件(self, 相对路径, 内容="合成内容"):
        p = self.ws / 相对路径
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(内容, encoding="utf-8")
        return p


# ---------------------------------------------------------------- 目录形状与图

class 目录形状(Base):
    def test_空图起手落下目录形状与图与两份视图(self):
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        for cell in CELLS:
            self.assertTrue((self.ws / cell).is_dir(), "缺格 %s" % cell)
        for name in ("图.json", "图视图.md", "图视图.json", "AGENTS.md", "CLAUDE.md"):
            self.assertTrue((self.ws / name).is_file(), "缺 %s" % name)
        self.assertEqual(self.graph()["模块"], [])

    def test_六格那套旧形状不再建(self):
        self.cli("init")
        for 旧 in ("收件箱", "指南", "模板", "材料/律师陈述"):
            self.assertFalse((self.ws / 旧).exists(), "还在建旧格 %s" % 旧)

    def test_预设图起手整份带进模块与节点(self):
        self.起手()
        self.assertEqual([m["标题"] for m in self.graph()["模块"]],
                         [标题 for 标题, _ in 工.菜园])
        self.assertEqual(sum(len(m["节点"]) for m in self.graph()["模块"]),
                         sum(len(节点) for _, 节点 in 工.菜园))

    def test_预设图起手把时限句一并拷进案件图(self):
        self.起手()
        self.assertEqual(self.node("施底肥")["时限"], "自松土完成之日起 3 日内（手册，示例）")

    def test_预设图的模板整份拷进参考模板(self):
        self.起手()
        got = sorted(p.name for p in (self.ws / "参考" / "模板").iterdir())
        self.assertEqual(got, ["播种登记.docx", "施肥记录.docx"])

    def test_空图起手不拷模板(self):
        self.造个人预设图()
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(list((self.ws / "参考" / "模板").iterdir()), [])
        self.assertIn("空图起手，不拷模板", r.out)

    def test_预设图没有模板格只报不拒(self):
        d = self.造个人预设图(名="没模板")
        shutil.rmtree(d / "模板")
        r = self.cli("init", "--preset", "没模板", "--owner", "个人")
        self.assertEqual(r.code, 0, r)
        self.assertIn("一件模板没拷", r.out)

    def test_参考模板下已有同名的不覆盖(self):
        self.造个人预设图()
        自己的 = self.丢一件("参考/模板/播种登记.docx", "律师自己那一份")
        r = self.cli("init", "--preset", "菜园", "--owner", "个人")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(自己的.read_text(encoding="utf-8"), "律师自己那一份")
        self.assertIn("没覆盖", r.out)


# ---------------------------------------------------------------- 目录非空与待归档

class 目录非空(Base):
    def test_目录非空不拒且原有的挪进待归档(self):
        self.丢一件("合同.pdf")
        self.丢一件("扫描/照片.jpg")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertTrue((self.ws / "待归档" / "合同.pdf").is_file())
        self.assertTrue((self.ws / "待归档" / "扫描" / "照片.jpg").is_file())
        self.assertFalse((self.ws / "合同.pdf").exists())
        self.assertIn("已挪进 待归档/", r.out)

    def test_点开头的一项不动(self):
        (self.ws / ".git").mkdir()
        self.丢一件(".codex-config")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertTrue((self.ws / ".git").is_dir())
        self.assertTrue((self.ws / ".codex-config").is_file())
        self.assertIn("点开头的 2 项没动", r.out)

    def test_待归档里已经有同名的就留在根上不动(self):
        self.丢一件("待归档/合同.pdf", "先丢进去那一份")
        撞的 = self.丢一件("合同.pdf", "根上那一份")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(撞的.read_text(encoding="utf-8"), "根上那一份")
        self.assertEqual((self.ws / "待归档" / "合同.pdf").read_text(encoding="utf-8"), "先丢进去那一份")
        self.assertIn("已经有同名的", r.out)

    def test_根上没东西也照说一句(self):
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertIn("没有要挪进 待归档/ 的东西", r.out)

    def test_归档索引不挪进待归档(self):
        self.丢一件("归档索引.md", "# 归档索引\n")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertTrue((self.ws / "归档索引.md").is_file())


# ---------------------------------------------------------------- 指针块

class 指针块(Base):
    def test_四项齐全(self):
        self.起手()
        text = self.指针块()
        for expected in ("预设图：菜园（个人）", "图.json", "图视图.md", "图视图.json",
                         "setup-case", "doit", "ask-loo0ng", "只读"):
            self.assertIn(expected, text, "指针块里缺 %s" % expected)
        self.assertEqual((self.ws / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_空图起手指针块记无(self):
        self.cli("init")
        self.assertIn("预设图：无（空图起手）", self.指针块())

    def test_指针块一条路径都不记(self):
        self.起手()
        text = self.指针块()
        for 片段 in (str(self.home), "预设图/", "/", "\\"):
            self.assertNotIn(片段, text, "指针块里出现了路径片段 %r（ADR-0023：只记名与归属）" % 片段)

    def test_已有的AGENTS追加在末尾原文不动(self):
        self.丢一件("AGENTS.md", "# 项目\n\nCodex 写的。\n")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        text = self.指针块()
        self.assertTrue(text.startswith("# 项目\n\nCodex 写的。\n"), text)
        self.assertIn("# 案件工作区", text)
        self.assertIn("原有内容一字未动", r.out)

    def test_已有的CLAUDE在开头加一行(self):
        self.丢一件("CLAUDE.md", "# 项目须知\n")
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertEqual((self.ws / "CLAUDE.md").read_text(encoding="utf-8"),
                         "@AGENTS.md\n# 项目须知\n")

    def test_已经有指针块就不写第二遍(self):
        self.cli("init")
        (self.ws / "图.json").unlink()
        before = self.指针块()
        r = self.cli("init")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.指针块(), before)
        self.assertIn("没有再写一遍", r.out)


# ---------------------------------------------------------------- 拒的情形

class 拒的情形(Base):
    def test_已有图就拒且一字不动(self):
        self.cli("init")
        before = (self.ws / "图.json").read_text(encoding="utf-8")
        r = self.cli("init")
        self.assertEqual(r.code, 1, r)
        self.assertIn("起手一案一次", r.err)
        self.assertEqual((self.ws / "图.json").read_text(encoding="utf-8"), before)

    def test_预设图与归属同给同不给(self):
        r = self.cli("init", "--preset", "菜园")
        self.assertEqual(r.code, 1, r)
        self.assertIn("同给同不给", r.err)
        self.assertFalse((self.ws / "图.json").exists())

    def test_只给归属也拒(self):
        r = self.cli("init", "--owner", "个人")
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists())

    def test_归属只认出厂与个人(self):
        r = self.cli("init", "--preset", "菜园", "--owner", "别处")
        self.assertEqual(r.code, 2, r)

    def test_解析不到预设图就一格不建一个字不写(self):
        r = self.cli("init", "--preset", "没有这份", "--owner", "个人")
        self.assertEqual(r.code, 1, r)
        self.assertIn("解析不到个人预设图「没有这份」", r.err)
        self.assertEqual(sorted(p.name for p in self.ws.iterdir()), [])

    def test_找不到preset_cli就拒(self):
        r = self.cli("init", "--preset", "菜园", "--owner", "个人",
                     "--preset-cli", str(self.tmp / "没有.py"))
        self.assertEqual(r.code, 1, r)
        self.assertIn("preset.py", r.err)
        self.assertEqual(sorted(p.name for p in self.ws.iterdir()), [])

    def test_找不到引擎就拒(self):
        r = self.cli("init", "--engine", str(self.tmp / "没有.py"))
        self.assertEqual(r.code, 1, r)
        self.assertIn("图引擎", r.err)
        self.assertEqual(sorted(p.name for p in self.ws.iterdir()), [])


# ---------------------------------------------------------------- 既有成品登记

class 既有成品登记(Base):
    def setUp(self):
        super().setUp()
        self.起手()
        self.成品 = self.丢一件("待归档/旧的下种记录.md", "起手前就写好的那一份")

    def register(self, *argv):
        return self.cli("register", "--node", "下种", "--file", "待归档/旧的下种记录.md",
                        "--words", "第 3 条按建议登记", *argv)

    def test_登记为已生成来源律师(self):
        r = self.register()
        self.assertEqual(r.code, 0, r)
        条目 = self.node("下种")["条目"]
        self.assertEqual([e["动作"] for e in 条目], ["生成"])
        self.assertEqual(条目[0]["来源"], "律师")

    def test_成品挪进节点的文书目录(self):
        self.register()
        目标 = self.ws / "文书" / "播种" / "下种" / "下种.md"
        self.assertTrue(目标.is_file())
        self.assertEqual(目标.read_text(encoding="utf-8"), "起手前就写好的那一份")
        self.assertFalse(self.成品.exists(), "原处该已经没有了")
        self.assertEqual(self.node("下种")["条目"][0]["文书"], "文书/播种/下种/下种.md")

    def test_审查报告只有一行且说了律师自写(self):
        self.register()
        报告 = self.ws / "文书" / "播种" / "下种" / "下种-审查报告.md"
        self.assertTrue(报告.is_file())
        行 = [line for line in 报告.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(行), 1, 行)
        self.assertTrue(行[0].startswith("律师自写"), 行[0])
        self.assertIn("第 3 条按建议登记", 行[0])
        self.assertEqual(self.node("下种")["条目"][0]["审查报告"],
                         "文书/播种/下种/下种-审查报告.md")

    def test_登记不确认任何节点(self):
        self.register()
        self.assertEqual(self.view()["模块"][1]["节点"][1]["状态"], "已生成")
        动作 = [e["动作"] for m in self.graph()["模块"] for n in m["节点"] for e in n["条目"]]
        self.assertEqual(动作, ["生成"], "起手只该留下这一条生成条目")

    def test_按节点id也登记得上(self):
        r = self.cli("register", "--node", "n-2-2", "--file", "待归档/旧的下种记录.md",
                     "--words", "按建议")
        self.assertEqual(r.code, 0, r)
        self.assertTrue((self.ws / "文书" / "播种" / "下种" / "下种.md").is_file())

    def test_图里没这个节点就拒(self):
        r = self.cli("register", "--node", "没有这个节点", "--file", "待归档/旧的下种记录.md",
                     "--words", "按建议")
        self.assertEqual(r.code, 1, r)
        self.assertIn("图里没有节点", r.err)
        self.assertTrue(self.成品.is_file(), "拒了就一个字不动")

    def test_找不到文件就拒(self):
        r = self.cli("register", "--node", "下种", "--file", "待归档/不存在.md", "--words", "按建议")
        self.assertEqual(r.code, 1, r)
        self.assertIn("找不到", r.err)

    def test_越界路径就拒(self):
        for 越界 in ("../外面.md", "C:/绝对.md", "待归档\\反斜杠.md"):
            r = self.cli("register", "--node", "下种", "--file", 越界, "--words", "按建议")
            self.assertEqual(r.code, 1, (越界, r))
            self.assertIn("--file", r.err)

    def test_节点已经有文书就拒且不覆盖(self):
        self.assertEqual(self.register().code, 0)
        再来 = self.丢一件("待归档/旧的下种记录.md", "第二份")
        r = self.register()
        self.assertEqual(r.code, 1, r)
        self.assertIn("登记不覆盖", r.err)
        self.assertEqual((self.ws / "文书" / "播种" / "下种" / "下种.md").read_text(encoding="utf-8"),
                         "起手前就写好的那一份")
        self.assertTrue(再来.is_file())

    def test_引擎拒写时成品挪回原处报告撤回(self):
        # 节点先记不适用（终态），引擎会拒掉这一条生成条目
        工.跑引擎("--graph", self.ws / "图.json", "not-applicable", "--node", "下种",
                  "--words", "这一项本案不适用", 须过=True)
        r = self.register()
        self.assertEqual(r.code, 1, r)
        self.assertIn("已挪回", r.err)
        self.assertTrue(self.成品.is_file(), "成品该挪回原处")
        self.assertFalse((self.ws / "文书" / "播种").exists(), "空出来的文书目录该收掉")

    def test_没有图就拒(self):
        空的 = self.tmp / "不是工作区"
        空的.mkdir()
        r = self.cli("register", "--node", "下种", "--file", "待归档/旧的下种记录.md",
                     "--words", "按建议", workspace=空的)
        self.assertEqual(r.code, 1, r)
        self.assertIn("先起手", r.err)


if __name__ == "__main__":
    unittest.main()
