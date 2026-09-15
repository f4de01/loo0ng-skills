"""每个种子回放一遍，看工作区状态与各自 状态.md 说的一致（#20 验收）。

运行：python -m unittest tests/evals/test_seeds.py

用跑器自己的种子接口回放（scripts/skill-eval.py 的 replay_seed），所以这里测的就是 eval 拿到的那个工作区。
「家」经 LOO0NG_HOME 指到一个临时目录，跑完连它一起删，不碰真的 ~/.loo0ng（ADR-0015 只生不存）。
带 docx 手术的种子（兜底、拒改、填过黄）要 python-docx，与 tests/to-docx 同一条依赖。
"""
import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
EVALS = REPO / "evals" / "用例"
SEEDS = REPO / "evals" / "种子"
RUNNER = REPO / "scripts" / "skill-eval.py"

spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

目录 = ("待归档", "材料", "参考/模板", "参考/指南", "文书")
旧形状 = ("收件箱", "指南", "模板", "材料/律师陈述", ".活图家", "领域图.json")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class 回放(unittest.TestCase):
    """一个种子一个临时工作区，setUpClass 回放一次、本类的几条断言共用。"""
    种子 = ""

    @classmethod
    def setUpClass(cls):
        if not cls.种子:
            raise unittest.SkipTest("基类")
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        cls.ws = cls.tmp / "ws"
        cls.ws.mkdir()
        cls.home = cls.tmp / "home"
        cls.was = os.environ.get(runner.HOME_ENV)
        # 回放失败时 unittest 不调 tearDownClass，善后挂在 addClassCleanup 上：
        # 否则临时工作区留在盘上，LOO0NG_HOME 还指着一个已经没了的路径，后面几个类跟着脏。
        cls.addClassCleanup(cls.还原环境, cls.was)
        cls.addClassCleanup(runner.remove_workspace, cls.tmp)
        os.environ[runner.HOME_ENV] = str(cls.home)
        runner.replay_seed(EVALS, cls.种子, cls.ws)

    @staticmethod
    def 还原环境(was):
        if was is None:
            os.environ.pop(runner.HOME_ENV, None)
        else:
            os.environ[runner.HOME_ENV] = was

    def graph(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def view(self):
        return json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)

    def view_node(self, title):
        for m in self.view()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("视图里找不到节点「%s」" % title)

    def 动作(self, title):
        return [e["动作"] for e in self.node(title)["条目"]]

    def assert工作区形状(self):
        for d in 目录:
            self.assertTrue((self.ws / d).is_dir(), "缺格 %s" % d)
        for name in ("图.json", "图视图.md", "图视图.json", "AGENTS.md", "CLAUDE.md"):
            self.assertTrue((self.ws / name).is_file(), "缺 %s" % name)
        for 旧 in 旧形状:
            self.assertFalse((self.ws / 旧).exists(), "工作区里还有旧形状的 %s" % 旧)
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("skills/", agents.replace("\\", "/"), "指针块不记路径（ADR-0023）：不许指进 skill 包里")
        self.assertTrue((self.ws / ".基线.json").is_file() or self.种子 in ("填过黄",), "路由种子要写基线")


class 空目录(回放):
    种子 = "空目录"

    def test_还不是工作区_根上六件_家里有菜园(self):
        self.assertFalse((self.ws / "图.json").exists())
        names = sorted(p.name for p in self.ws.iterdir())
        self.assertEqual(len(names), 6, names)
        self.assertTrue((self.home / "预设图" / "菜园" / "预设图.json").is_file(), "家里该有个人预设图「菜园」")


class 空图(回放):
    种子 = "空图"

    def test_空图(self):
        self.assert工作区形状()
        self.assertEqual(self.graph()["模块"], [])
        self.assertEqual(self.view()["前方"], [])
        self.assertEqual(list((self.ws / "参考" / "模板").iterdir()), [], "空图起手不拷模板")


class 图引擎(回放):
    种子 = "图引擎"

    def test_菜园整份起手(self):
        self.assert工作区形状()
        self.assertEqual([m["标题"] for m in self.graph()["模块"]], ["整地", "播种", "养护", "收获"])
        self.assertEqual(sum(len(m["节点"]) for m in self.graph()["模块"]), 9)
        self.assertEqual(sorted(p.name for p in (self.ws / "参考" / "模板").iterdir()), ["播种登记.docx", "施肥记录.docx"])
        self.assertIn("预设图：菜园（个人）", (self.ws / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(self.view_node("施底肥")["时限"], "自松土完成之日起 3 日内（手册，示例）")


class 待归档(回放):
    种子 = "待归档"

    def test_三件在待归档(self):
        self.assert工作区形状()
        self.assertEqual(sorted(p.name for p in (self.ws / "待归档").iterdir()),
                         ["合作社种植要求.md", "地块记录.txt", "播种日志空表.md"])
        self.assertFalse((self.ws / "归档索引.md").exists())


class 模板(回放):
    种子 = "模板"

    def test_官方模板在参考模板下(self):
        self.assert工作区形状()
        self.assertTrue((self.ws / "参考" / "模板" / "1-2.关于管理人印章备案的报告.docx").is_file())


class 指南(回放):
    种子 = "指南"

    def test_指南归进了参考指南并进索引(self):
        self.assert工作区形状()
        self.assertTrue((self.ws / "参考" / "指南" / "种植指南.md").is_file())
        self.assertEqual(list((self.ws / "待归档").iterdir()), [])
        self.assertIn("参考/指南/种植指南.md", (self.ws / "归档索引.md").read_text(encoding="utf-8"))


class 另存(回放):
    种子 = "另存"

    def test_自加节点已确认_家在家文件里(self):
        self.assert工作区形状()
        自加 = "乙家甲年乙月丙日南墙菜畦补种记录"
        self.assertEqual(self.动作("松土"), ["生成", "确认"])
        self.assertEqual(self.动作(自加), ["生成", "确认"])
        家 = json.loads((self.ws / ".家.json").read_text(encoding="utf-8"))
        self.assertEqual(pathlib.Path(家["预设图根"]), self.home / "预设图")
        self.assertTrue((self.home / "预设图" / "菜园" / "预设图.json").is_file())


class 在办中(回放):
    种子 = "在办中"

    def test_状态照状态md(self):
        self.assert工作区形状()
        self.assertEqual(len(self.graph()["模块"]), 12)
        self.assertEqual(sum(len(m["节点"]) for m in self.graph()["模块"]), 72)
        self.assertEqual(len(list((self.ws / "参考" / "模板").iterdir())), 19)
        self.assertEqual(self.动作("管理人承诺书及团队人员"), ["生成", "确认"])
        self.assertEqual(self.view_node("管理人承诺书及团队人员")["高亮"], "已清")
        self.assertEqual(self.动作("管理人印章备案报告"), ["生成"])
        self.assertEqual(self.view_node("管理人印章备案报告")["高亮"], "未清")
        self.assertEqual(self.view()["前方"][0]["节点"][0]["标题"], "管理人工作计划")

    def test_材料归了_指南还在待归档_律师说过的四行(self):
        self.assertTrue((self.ws / "材料" / "债务人移交物品清单.txt").is_file())
        self.assertIn("材料/债务人移交物品清单.txt", (self.ws / "归档索引.md").read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in (self.ws / "待归档").iterdir()], ["甲法院破产案件管理人工作提示.md"])
        行 = [l for l in (self.ws / "材料" / "律师说过的.md").read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(行), 4)


class 两份待确认(回放):
    种子 = "两份待确认"

    def test_一份已清一份未清(self):
        self.assert工作区形状()
        self.assertEqual(self.动作("管理人承诺书及团队人员"), ["生成", "确认"])
        self.assertEqual(self.view_node("管理人印章备案报告")["高亮"], "已清")
        self.assertEqual(self.view_node("管理人银行账户备案报告")["高亮"], "未清")
        self.assertEqual(self.view()["前方"][0]["节点"][0]["标题"], "管理人工作计划")


class 重出(回放):
    种子 = "重出"

    def test_重出的回到已生成(self):
        self.assert工作区形状()
        self.assertEqual(self.动作("管理人承诺书及团队人员"), ["生成", "确认", "生成"])
        n = self.view_node("管理人承诺书及团队人员")
        self.assertEqual((n["状态"], n["高亮"]), ("已生成", "已清"))
        self.assertNotIn("最近确认", n)
        self.assertEqual(self.view_node("管理人印章备案报告")["状态"], "已确认")


class 跳着走(回放):
    种子 = "跳着走"

    def test_两块各一个已确认(self):
        self.assert工作区形状()
        self.assertEqual(self.动作("管理人承诺书及团队人员"), ["生成", "确认"])
        self.assertEqual(self.动作("债权表"), ["生成", "确认"])
        承 = self.view_node("管理人承诺书及团队人员")["最近确认"]["时间"]
        债 = self.view_node("债权表")["最近确认"]["时间"]
        self.assertLess(承, 债, "债权表要确认得更晚（上一完成靠它）")
        self.assertEqual(self.view()["前方"][0]["节点"][0]["标题"], "管理人工作计划")


class 整块不走(回放):
    种子 = "整块不走"

    def test_模块不适用(self):
        self.assert工作区形状()
        self.assertEqual(self.动作("和解协议"), ["不适用"])
        self.assertEqual(self.动作("裁定认可和解协议并终结破产程序的申请"), ["不适用"])
        前方 = [n["标题"] for m in self.view()["前方"] for n in m["节点"]]
        self.assertNotIn("和解协议", 前方)
        self.assertEqual(前方[0], "管理人工作计划")


class 自加节点(回放):
    种子 = "自加节点"

    def test_改标题与自加(self):
        self.assert工作区形状()
        n = self.node("承诺书")
        self.assertEqual(n["id"], "n-chengnuoshu")
        self.assertTrue(n.get("时限"), "改标题不动时限")
        self.assertEqual(self.动作("承诺书"), ["生成"])
        self.assertEqual(self.view_node("承诺书")["高亮"], "已清")
        self.assertEqual(self.view()["前方"][0]["节点"][0]["标题"], "补充材料说明")


class 兜底(回放):
    种子 = "兜底"

    def test_待归档里那件律师自写的docx(self):
        self.assert工作区形状()
        成品 = self.ws / "待归档" / "印章备案-我自己写的.docx"
        self.assertTrue(成品.is_file())
        with zipfile.ZipFile(str(成品)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        self.assertIn("甲乙丙", xml)
        self.assertNotIn("XX年", xml, "槽该全填了")
        self.assertNotIn('w:highlight w:val="yellow"', xml, "全填了就没有一处黄")
        self.assertEqual(self.动作("管理人印章备案报告"), ["生成"], "登记是办节点那一句话的事，种子只摆好起点")


class 拒改(回放):
    种子 = "拒改"

    def test_模板钉了域代码且施加必拒(self):
        self.assert工作区形状()
        模板 = self.ws / "参考" / "模板" / "1-3.关于管理人银行账户备案的报告.docx"
        with zipfile.ZipFile(str(模板)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        self.assertIn("w:instrText", xml)
        self.assertEqual(self.动作("管理人银行账户备案报告"), [])
        # 回放自己复核过空差量与填一个槽都退 1；这里只再核一次「一个字不写」：节点目录不存在。
        self.assertFalse((self.ws / "文书" / "接受指定与报备" / "管理人银行账户备案报告").exists())


class 填过黄(回放):
    种子 = "填过黄"

    def test_律师动过的三处与插的段(self):
        self.assert工作区形状()
        文书 = self.ws / "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告.docx"
        self.assertTrue(文书.is_file())
        self.assertEqual(self.动作("管理人印章备案报告"), ["生成"])
        self.assertEqual(self.view_node("管理人印章备案报告")["高亮"], "未清")
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(str(文书)) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        段 = ["".join(t.text or "" for t in p.iter(_W + "t")) for p in root.iter(_W + "p")]
        self.assertIn("律师补记：印模以刻章回执为准。", 段)
        self.assertIn("甲年乙月丙日", 段, "启用时间填了")
        self.assertIn("甲年乙月丁日", 段, "落款日期填了")
        self.assertTrue(any("XXX公安局" in s for s in 段), "公安局名没动")
        报告 = (self.ws / "文书/接受指定与报备/管理人印章备案报告/管理人印章备案报告-审查报告.md").read_text(encoding="utf-8")
        for h in ("## 生成依据", "## 高亮清单", "## 施加原话", "## 时限"):
            self.assertIn(h, 报告)
        self.assertIn("高亮清单 3 处", 报告)


class 每个种子都有状态说明(unittest.TestCase):
    def test_种子目录齐全(self):
        有 = sorted(p.name for p in SEEDS.iterdir() if p.is_dir())
        测了 = sorted(c.种子 for c in 回放.__subclasses__())
        self.assertEqual(有, 测了, "每个种子都要在这里回放一遍")
        for p in SEEDS.iterdir():
            if p.is_dir():
                self.assertTrue((p / "回放.py").is_file(), "%s 缺 回放.py" % p.name)
                self.assertTrue((p / "状态.md").is_file(), "%s 缺 状态.md" % p.name)

    def test_每个用例的种子都存在(self):
        for c in EVALS.iterdir():
            if not (c / "用例.json").is_file():
                continue
            种子 = json.loads((c / "用例.json").read_text(encoding="utf-8")).get("种子")
            if 种子:
                self.assertTrue((SEEDS / 种子 / "回放.py").is_file(), "用例 %s 指着不存在的种子 %s" % (c.name, 种子))


if __name__ == "__main__":
    unittest.main()
