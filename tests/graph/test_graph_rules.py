"""引擎的规则面：条目与状态、拒写、原子写、构成操作、预设图编辑、另存、派生视图、目录名、高亮。

运行：python -m unittest discover -s tests/graph -p 'test_*.py' -t .
共用 test_graph.py 里的 EngineCase（临时根目录 + 由 tests/共用/工作区.py 造的工作区与预设图）。
"""
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_graph import EngineCase, SCRIPT, graph, 工  # noqa: E402


# ---------------------------------------------------------------- 条目与状态

class EntryTest(EngineCase):
    def setUp(self):
        super().setUp()
        self.ws = self.整份工作区()

    def test_状态跟着最后一条条目走(self):
        ws = self.ws
        self.assertEqual(graph.node_state(ws.节点("松土")), "未生成")
        ws.出一版("整地", "松土")
        self.assertEqual(graph.node_state(ws.节点("松土")), "已生成")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认 松土")
        self.assertEqual(graph.node_state(ws.节点("松土")), "已确认")
        ws.出一版("整地", "松土")
        n = ws.节点("松土")
        self.assertEqual(graph.node_state(n), "已生成", "已确认要改就重出，节点回到已生成")
        self.assertEqual([e["动作"] for e in n["条目"]], ["生成", "确认", "生成"], "旧的确认留在条目里")
        self.assertEqual(n["条目"][1]["原话"], "确认 松土")

    def test_生成条目就两条相对路径(self):
        ws = self.ws
        ws.出一版("整地", "施底肥")
        e = ws.节点("施底肥")["条目"][0]
        self.assertEqual(set(e), {"动作", "时间", "来源", "文书", "审查报告"})
        self.assertEqual(e["来源"], "agent")
        self.assertEqual(e["文书"], "文书/整地/施底肥/施底肥.docx")
        self.assertRegex(e["时间"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

    def test_律师自写的兜底件来源记律师(self):
        ws = self.ws
        self.ok(ws, "generate", "--node", "浇水", "--doc", "b.docx", "--review", "b-审查报告.md",
                "--lawyer-written")
        self.assertEqual(ws.节点("浇水")["条目"][0]["来源"], "律师")

    def test_不适用是终态(self):
        ws = self.ws
        self.ok(ws, "not-applicable", "--node", "搭架", "--words", "搭架 不适用")
        n = ws.节点("搭架")
        self.assertEqual(graph.node_state(n), "不适用")
        self.assertEqual(n["条目"][0]["来源"], "律师")
        self.rejected(ws, "generate", "--node", "搭架", "--doc", "c.docx", "--review", "c-审查报告.md")
        self.rejected(ws, "not-applicable", "--node", "搭架", "--words", "再来一次")

    def test_已确认的不能不适用(self):
        ws = self.ws
        ws.出一版("整地", "松土")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认")
        r = self.rejected(ws, "not-applicable", "--node", "松土", "--words", "松土 不适用")
        self.assertIn("已确认", r.err)
        self.assertEqual(len(ws.节点("松土")["条目"]), 2)

    def test_确认要先有一版文书(self):
        ws = self.ws
        self.rejected(ws, "confirm", "--node", "松土", "--words", "确认")
        ws.出一版("整地", "松土")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认")
        self.rejected(ws, "confirm", "--node", "松土", "--words", "再确认一次")

    def test_没有改条目删条目删节点这些子命令(self):
        """条目只追加，节点永不删：这些名字都是用法错误（退出码 2）。"""
        for bad in ("edit-entry", "delete-entry", "remove-entry", "delete-node", "remove-node"):
            self.assertEqual(self.ws.调(bad, "--node", "松土").code, 2, bad)

    def test_生成的路径须是相对正斜杠(self):
        ws = self.ws
        for bad in ("C:/x/a.docx", "文书\\松土\\a.docx", "../a.docx", "/a.docx"):
            r = self.rejected(ws, "generate", "--node", "松土", "--doc", bad, "--review", "b.md")
            self.assertIn("相对", r.err, bad)
        self.assertEqual(ws.节点("松土")["条目"], [])

    def test_预设图上不能追加条目(self):
        目录 = self.预设图()
        r = 工.跑引擎("--graph", 目录 / graph.PRESET_FILENAME, "--kind", "preset",
                      "generate", "--node", "松土", "--doc", "a.docx", "--review", "b.md")
        self.assertEqual(r.code, 1, r)
        self.assertIn("预设图没有条目", r.err)

    def test_图里没有的节点不去别处找(self):
        """图自足（ADR-0023）：图里没有就是没有，不再按预设图惰性带入。"""
        ws = self.空图工作区()
        r = self.rejected(ws, "generate", "--node", "下种", "--doc", "a.docx", "--review", "b.md")
        self.assertIn("add-node", r.err)
        self.assertEqual(ws.模块标题(), [])


class ModuleNotApplicableTest(EngineCase):
    def test_模块不适用给每个节点各记一条(self):
        ws = self.整份工作区()
        self.ok(ws, "not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        for n in ws.模块("养护")["节点"]:
            self.assertEqual(graph.node_state(n), "不适用")
            self.assertEqual(n["条目"][0]["原话"], "模块 养护 不适用")
        self.assertEqual(graph.module_state(ws.模块("养护")), "不适用")
        self.assertEqual(graph.node_state(ws.节点("松土")), "未生成", "别的模块不受影响")

    def test_已是不适用的跳过律师自加的也记(self):
        ws = self.整份工作区()
        self.ok(ws, "add-node", "--module", "养护", "--title", "松绑")
        self.ok(ws, "not-applicable", "--node", "除草", "--words", "除草 不适用")
        self.ok(ws, "not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        self.assertEqual(len(ws.节点("除草")["条目"]), 1, "已是不适用的不再追加")
        self.assertEqual(graph.node_state(ws.节点("松绑")), "不适用")

    def test_模块里有已确认的整个模块不能不适用(self):
        ws = self.整份工作区()
        ws.出一版("养护", "浇水")
        self.ok(ws, "confirm", "--node", "浇水", "--words", "确认")
        r = self.rejected(ws, "not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        self.assertIn("浇水", r.err)
        self.assertEqual(graph.node_state(ws.节点("除草")), "未生成", "整个操作不落盘")

    def test_空模块没有可记的对象(self):
        ws = self.空图工作区()
        self.ok(ws, "add-module", "--title", "甲")
        self.rejected(ws, "not-applicable", "--module", "甲", "--words", "甲 不适用")


# ---------------------------------------------------------------- 原子写与拒写不动文件

class AtomicWriteTest(EngineCase):
    def test_拒写时文件逐字节不变(self):
        ws = self.整份工作区()
        before = {p.name: p.read_bytes() for p in ws.根.iterdir() if p.is_file()}
        self.rejected(ws, "delete-module", "--module", "整地")
        after = {p.name: p.read_bytes() for p in ws.根.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_写成功不留临时文件(self):
        ws = self.整份工作区()
        self.ok(ws, "add-module", "--title", "甲")
        self.assertEqual(sorted(p.name for p in ws.根.iterdir() if p.is_file()),
                         ["图.json", "图视图.json", "图视图.md"])

    def test_替换失败保住原件(self):
        ws = self.整份工作区()
        before = ws.图.read_bytes()
        with mock.patch.object(graph.os, "replace", side_effect=OSError("模拟替换失败")):
            with self.assertRaises(OSError):
                ws.调("add-module", "--title", "甲")
        self.assertEqual(ws.图.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in ws.根.iterdir() if p.is_file()),
                         ["图.json", "图视图.json", "图视图.md"])


# ---------------------------------------------------------------- 构成操作

class CompositionTest(EngineCase):
    def setUp(self):
        super().setUp()
        self.ws = self.整份工作区()

    def test_改标题不动id与条目(self):
        ws = self.ws
        ws.出一版("播种", "下种")
        self.ok(ws, "rename-node", "--node", "下种", "--title", "播种入土")
        n = ws.节点("播种入土")
        self.assertEqual(n["id"], "n-2-2")
        self.assertEqual(len(n["条目"]), 1)
        self.rejected(ws, "rename-node", "--node", "播种入土", "--title", "选种")

    def test_跨模块移动与排序(self):
        ws = self.ws
        self.ok(ws, "move-node", "--node", "搭架", "--module", "播种", "--first")
        self.assertEqual(ws.节点标题("播种"), ["搭架", "选种", "下种"])
        self.assertEqual(ws.节点标题("养护"), ["浇水", "除草"])
        self.ok(ws, "move-node", "--node", "搭架", "--after", "选种")
        self.assertEqual(ws.节点标题("播种"), ["选种", "搭架", "下种"])
        self.rejected(ws, "move-node", "--node", "搭架", "--before", "浇水")

    def test_模块改名排序与删空模块(self):
        ws = self.ws
        self.ok(ws, "rename-module", "--module", "养护", "--title", "照料")
        self.ok(ws, "move-module", "--module", "照料", "--first")
        self.assertEqual(ws.模块标题(), ["照料", "整地", "播种", "收获"])
        r = self.rejected(ws, "delete-module", "--module", "照料")
        self.assertIn("节点永不删", r.err)
        for t in ("浇水", "除草", "搭架"):
            self.ok(ws, "move-node", "--node", t, "--module", "收获")
        self.ok(ws, "delete-module", "--module", "照料")
        self.assertEqual(ws.模块标题(), ["整地", "播种", "收获"])
        self.assertEqual(ws.节点标题("收获"), ["采摘", "记账", "浇水", "除草", "搭架"], "节点一个不丢")

    def test_新增节点落在指定模块与位置(self):
        ws = self.ws
        self.ok(ws, "add-node", "--module", "整地", "--title", "翻晒", "--first")
        self.assertEqual(ws.节点标题("整地"), ["翻晒", "松土", "施底肥"])
        self.assertRegex(ws.节点("翻晒")["id"], r"^n-[0-9a-f]{8}$", "案件图的 id 由引擎生成")
        self.rejected(ws, "add-node", "--module", "没有这个模块", "--title", "别的")

    def test_空白模板只记文件名(self):
        ws = self.ws
        self.ok(ws, "set-template", "--node", "松土", "--template", "松土记录.docx")
        self.assertEqual(ws.节点("松土")["空白模板"], "松土记录.docx")
        self.ok(ws, "set-template", "--node", "松土", "--template", "无")
        self.assertEqual(ws.节点("松土")["空白模板"], "无")

    def test_案件图上给id即拒(self):
        """案件图里 id 由引擎生成；冒用预设图的 id 会让别处按 id 认错节点，所以拒。"""
        ws = self.ws
        r = self.rejected(ws, "add-node", "--module", "播种", "--title", "自加", "--id", "n-1-2")
        self.assertIn("--id", r.err)
        self.rejected(ws, "add-module", "--title", "自加模块", "--id", "m-x")


class PresetKindTest(EngineCase):
    """开发者用同一引擎编辑预设图：可写时限、可给 id、无条目、不出视图。"""

    def test_造预设图写时限不出视图(self):
        目录 = self.tmp / "手造"
        目录.mkdir()
        图 = 目录 / graph.PRESET_FILENAME
        基 = ["--graph", 图, "--kind", "preset"]

        def ok(*a):
            r = 工.跑引擎(*基, *a)
            self.assertEqual(r.code, 0, r)

        ok("init", "--empty")
        ok("add-module", "--title", "甲", "--id", "m-jia")
        ok("add-node", "--module", "甲", "--title", "甲一", "--id", "n-jia1", "--time-limit", "三日内（示例）")
        ok("add-node", "--module", "甲", "--title", "甲二", "--id", "n-jia2")
        ok("set-time-limit", "--node", "甲二", "--time-limit", "五日内（示例）")
        ok("set-time-limit", "--node", "甲一")
        ok("validate")
        data = __import__("json").loads(图.read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"格式版本", "模块"})
        self.assertNotIn("时限", data["模块"][0]["节点"][0])
        self.assertEqual(data["模块"][0]["节点"][1]["时限"], "五日内（示例）")
        self.assertEqual(sorted(p.name for p in 目录.iterdir()), [graph.PRESET_FILENAME],
                         "预设图目录不出视图")
        ws = 工.起工作区(self.tmp / "案件", 预设图=目录)
        self.assertEqual(ws.节点("甲二")["时限"], "五日内（示例）")

    def test_预设图起手不收preset(self):
        r = 工.跑引擎("--graph", self.tmp / "x.json", "--kind", "preset",
                      "init", "--preset", str(self.预设图()))
        self.assertEqual(r.code, 1, r)
        self.assertIn("--preset 只对案件图", r.err)


# ---------------------------------------------------------------- 另存

class ExportPresetTest(EngineCase):
    def test_另存剥条目留构成模板时限与id(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认 松土")
        self.ok(ws, "not-applicable", "--node", "搭架", "--words", "搭架 不适用")
        self.ok(ws, "add-node", "--module", "整地", "--title", "翻晒", "--template", "翻晒记录.docx")
        before = ws.图.read_bytes()

        出 = self.tmp / "个人预设图" / "菜园二版"
        r = self.ok(ws, "export-preset", "--out", str(出))
        self.assertIn("一字未动", r.out)
        self.assertEqual(ws.图.read_bytes(), before, "另存不碰输入图")

        import json
        preset = json.loads((出 / graph.PRESET_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(set(preset), {"格式版本", "模块"})
        节点 = {n["标题"]: n for m in preset["模块"] for n in m["节点"]}
        self.assertEqual([m["标题"] for m in preset["模块"]], ["整地", "播种", "养护", "收获"])
        self.assertEqual(list(节点), ["松土", "施底肥", "翻晒", "选种", "下种",
                                      "浇水", "除草", "搭架", "采摘", "记账"],
                         "节点一个不丢，不适用的也在：不适用是条目，不是构成")
        for n in 节点.values():
            self.assertEqual(n["条目"], [], "条目与不适用记录都剥掉")
        self.assertEqual(节点["施底肥"]["id"], "n-1-2", "id 保留")
        self.assertEqual(节点["施底肥"]["时限"], "自松土完成之日起 3 日内（手册，示例）", "时限保留")
        self.assertEqual(节点["翻晒"]["空白模板"], "翻晒记录.docx", "空白模板保留")
        self.assertEqual(节点["松土"]["空白模板"], "无")

    def test_另存出来的东西能再起手(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        出 = self.tmp / "个人预设图" / "菜园二版"
        self.ok(ws, "export-preset", "--out", str(出))
        新 = 工.起工作区(self.tmp / "另一案", 预设图=出)
        self.assertEqual(新.模块标题(), ["整地", "播种", "养护", "收获"])
        self.assertEqual(新.节点("松土")["条目"], [])

    def test_另存不覆盖已有的(self):
        ws = self.整份工作区()
        出 = self.tmp / "个人预设图" / "菜园二版"
        self.ok(ws, "export-preset", "--out", str(出))
        r = self.rejected(ws, "export-preset", "--out", str(出))
        self.assertIn("不覆盖", r.err)

    def test_空图也另存得出来(self):
        ws = self.空图工作区()
        self.ok(ws, "export-preset", "--out", str(self.tmp / "空的"))
        import json
        self.assertEqual(json.loads((self.tmp / "空的" / graph.PRESET_FILENAME)
                                    .read_text(encoding="utf-8"))["模块"], [])


# ---------------------------------------------------------------- 目录名转义

class DirnameTest(EngineCase):
    def test_用不了的字符换成全角(self):
        self.assertEqual(graph.dirname_of("债权申报/审查表"), "债权申报／审查表")
        self.assertEqual(graph.dirname_of('甲:乙*丙?丁"戊<己>庚|辛\\壬'),
                         "甲：乙＊丙？丁＂戊＜己＞庚｜辛＼壬")
        self.assertEqual(graph.dirname_of("普通的标题"), "普通的标题", "没问题的字符一个不动")

    def test_视图给出目录名(self):
        ws = self.空图工作区()
        self.ok(ws, "add-module", "--title", "第一批/第二批")
        self.ok(ws, "add-node", "--module", "第一批/第二批", "--title", "债权申报:审查")
        视图 = ws.读视图()
        self.assertEqual(视图["模块"][0]["目录名"], "第一批／第二批")
        self.assertEqual(视图["模块"][0]["标题"], "第一批/第二批", "标题原样，只有目录名转义")
        self.assertEqual(ws.视图节点("债权申报:审查")["目录名"], "债权申报：审查")

    def test_转义后撞车即拒(self):
        ws = self.空图工作区()
        self.ok(ws, "add-module", "--title", "甲")
        self.ok(ws, "add-node", "--module", "甲", "--title", "一/二")
        r = self.rejected(ws, "add-node", "--module", "甲", "--title", "一／二")
        self.assertIn("同一个目录名", r.err)
        self.assertNotIn("手改", r.err, "律师打错一句话，拒绝消息不该说成文件被手改过")
        self.assertEqual(ws.节点标题("甲"), ["一/二"])
        self.ok(ws, "add-node", "--module", "甲", "--title", "三/四")
        self.rejected(ws, "rename-node", "--node", "三/四", "--title", "一／二")
        # 模块与节点是 文书/<模块>/<节点>/ 的两层目录，各自唯一即可，不互相撞
        self.ok(ws, "rename-module", "--module", "甲", "--title", "一／二")

    def test_空标题即拒(self):
        ws = self.空图工作区()
        self.ok(ws, "add-module", "--title", "甲")
        for 命令 in (["add-module", "--title", "  "],
                     ["add-node", "--module", "甲", "--title", "  "],
                     ["rename-module", "--module", "甲", "--title", "  "]):
            r = self.rejected(ws, *命令)
            self.assertIn("标题不能是空的", r.err)
            self.assertNotIn("手改", r.err)


# ---------------------------------------------------------------- 派生视图、前方、高亮

class ViewTest(EngineCase):
    def test_整份起手后前方就是全部节点(self):
        ws = self.整份工作区()
        视图 = ws.读视图()
        self.assertEqual(视图["格式版本"], ws.读图()["格式版本"])
        self.assertEqual(视图["源图"], "图.json")
        self.assertIn("生成时间", 视图)
        self.assertNotIn("领域", 视图)
        self.assertEqual([m["标题"] for m in 视图["前方"]], ["整地", "播种", "养护", "收获"])
        for m in 视图["模块"]:
            self.assertEqual(m["状态"], "进行中")
            for n in m["节点"]:
                self.assertNotIn("来源", n, "视图里不再有来源列（ADR-0023）")
                self.assertEqual(n["状态"], "未生成")
        self.assertEqual(ws.视图节点("施底肥")["时限"], "自松土完成之日起 3 日内（手册，示例）")
        self.assertNotIn("时限", ws.视图节点("松土"))
        self.assertIn("自松土完成之日起 3 日内（手册，示例）", ws.读视图文())

    def test_前方只从案件图算(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认")
        self.ok(ws, "not-applicable", "--node", "施底肥", "--words", "不适用")
        ws.出一版("播种", "选种")
        前方 = {m["标题"]: [n["标题"] for n in m["节点"]] for m in ws.读视图()["前方"]}
        self.assertNotIn("整地", 前方, "已确认与不适用的不在前方，整个模块就空了")
        self.assertEqual(前方["播种"], ["下种"], "已生成的不再是「还没生成」")
        self.assertEqual(前方["养护"], ["浇水", "除草", "搭架"])
        self.assertIn("## 前方", ws.读视图文())

    def test_前方带空白模板与时限(self):
        ws = self.整份工作区()
        n = [x for m in ws.读视图()["前方"] if m["标题"] == "整地" for x in m["节点"]][1]
        self.assertEqual((n["标题"], n["空白模板"]), ("施底肥", "施肥记录.docx"))
        self.assertEqual(n["时限"], "自松土完成之日起 3 日内（手册，示例）")
        self.assertNotIn("状态", n, "前方里的节点状态只有一个值，不必重复")

    def test_每个节点一列高亮是否已清(self):
        ws = self.整份工作区()
        self.assertEqual(ws.视图节点("松土")["高亮"], "无文书", "还没出件")
        ws.出一版("整地", "松土", 高亮=True)
        self.assertEqual(ws.视图节点("松土")["高亮"], "未清")
        self.assertIn("高亮未清", ws.读视图文())
        # 律师在 Word 里填完去了黄：同一路径覆盖，重算即改口
        工.写文书(ws.根 / ws.文书相对路径("整地", "松土"), ["甲方与乙方就本节点达成如下记载。"])
        self.ok(ws, "views")
        self.assertEqual(ws.视图节点("松土")["高亮"], "已清")

    def test_文书不在了算无文书(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土", 高亮=True)
        (ws.根 / ws.文书相对路径("整地", "松土")).unlink()
        self.ok(ws, "views")
        self.assertEqual(ws.视图节点("松土")["高亮"], "无文书")

    def test_读不出来的文书算未清(self):
        """证不出已清就不能说已清：这一列是提示律师去看那份文书，不是裁定。"""
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        (ws.根 / ws.文书相对路径("整地", "松土")).write_bytes("这不是个 zip".encode("utf-8"))
        self.ok(ws, "views")
        self.assertEqual(ws.视图节点("松土")["高亮"], "未清")

    def test_视图记最近一次生成与确认(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认 松土，可以报")
        n = ws.视图节点("松土")
        self.assertEqual(n["状态"], "已确认")
        self.assertEqual(n["最近生成"]["次数"], 1)
        self.assertEqual(n["最近生成"]["文书"], "文书/整地/松土/松土.docx")
        self.assertEqual(n["最近确认"]["原话"], "确认 松土，可以报")
        self.assertIn("「确认 松土，可以报」", ws.读视图文())
        ws.出一版("整地", "松土")
        n = ws.视图节点("松土")
        self.assertEqual(n["状态"], "已生成")
        self.assertEqual(n["最近生成"]["次数"], 2, "文书覆盖同一路径，第几次只在条目里留痕")
        self.assertNotIn("最近确认", n, "重出之后当前这一版还没被确认")
        self.assertEqual(len([e for e in n["条目"] if e["动作"] == "确认"]), 1, "旧的确认留在条目里")

    def test_模块状态三值(self):
        ws = self.整份工作区()
        self.ok(ws, "not-applicable", "--module", "养护", "--words", "养护 不适用")
        for t in ("松土", "施底肥"):
            ws.出一版("整地", t)
        self.ok(ws, "confirm", "--node", "松土", "--words", "确认")
        self.ok(ws, "not-applicable", "--node", "施底肥", "--words", "不适用")
        states = {m["标题"]: m["状态"] for m in ws.读视图()["模块"]}
        self.assertEqual(states, {"整地": "已完成", "播种": "进行中", "养护": "不适用", "收获": "进行中"})

    def test_views只重算视图不动图(self):
        ws = self.整份工作区()
        before = ws.图.read_bytes()
        self.ok(ws, "views")
        self.assertEqual(ws.图.read_bytes(), before)

    def test_空图的视图(self):
        ws = self.空图工作区()
        视图 = ws.读视图()
        self.assertEqual((视图["模块"], 视图["前方"]), ([], []))
        self.assertIn("（图里还没有模块）", ws.读视图文())

    def test_视图里不写破折号(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        self.assertNotIn(chr(0x2014), ws.读视图文(), "破折号不进视图")


# ---------------------------------------------------------------- 真实子进程（中文参数与输出）

class SubprocessTest(EngineCase):
    def test_子进程跑得起来中文参数与输出(self):
        import os
        import subprocess
        ws = self.整份工作区()
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        base = [sys.executable, str(SCRIPT), "--graph", str(ws.图)]

        def run(*extra):
            return subprocess.run(base + list(extra), capture_output=True, cwd=str(ws.根), env=env)

        r = run("generate", "--node", "下种", "--doc", "文书/播种/下种/下种.docx",
                "--review", "文书/播种/下种/下种-审查报告.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("已追加生成条目", r.stdout.decode("utf-8"))
        self.assertEqual(ws.节点("下种")["条目"][0]["文书"], "文书/播种/下种/下种.docx")
        r = run("confirm", "--node", "松土", "--words", "确认")
        self.assertEqual(r.returncode, 1)
        self.assertIn("拒写", r.stderr.decode("utf-8"))
        self.assertEqual(run("bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
