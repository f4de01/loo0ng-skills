"""skills/engineering/graph/scripts/graph.py 的起手与校验面（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/graph -p 'test_*.py' -t .

缝是引擎 CLI 加工作区里的文件：每个测试在临时目录里调 main(argv)，再读 图.json 与两份视图断言。
工作区与预设图都由 tests/共用/工作区.py 用引擎自己造（#12），不从 evals/种子 拷；领域一律是
合成小领域「菜园」，证明引擎不认破产语义（ADR-0015）。
"""
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

graph = 工.引擎
SCRIPT = 工.引擎脚本


class EngineCase(unittest.TestCase):
    """每个测试一个临时根目录：下面一格放预设图，一格放案件工作区。"""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="graph-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._第几个 = 0

    def 新目录(self, 前缀):
        """一个测试里可以起好几个工作区或预设图，各占一格，互不相扰。"""
        self._第几个 += 1
        return self.tmp / ("%s%d" % (前缀, self._第几个))

    def 预设图(self, 模块=None, 名="菜园"):
        return 工.造预设图(self.新目录("预设图"), 模块 if 模块 is not None else 工.菜园, 名=名)

    def 空图工作区(self):
        return 工.起工作区(self.新目录("案件"))

    def 整份工作区(self, 模块=None):
        return 工.起工作区(self.新目录("案件"), 预设图=self.预设图(模块))

    def ok(self, ws, *argv):
        r = ws.调(*argv)
        self.assertEqual(r.code, 0, r)
        return r

    def rejected(self, ws, *argv):
        r = ws.调(*argv)
        self.assertEqual(r.code, 1, r)
        return r


# ---------------------------------------------------------------- 起手只剩两条

class InitTest(EngineCase):
    def test_空图起手落图与两份视图(self):
        ws = self.空图工作区()
        self.assertEqual(ws.读图(), {"格式版本": graph.FORMAT_VERSION, "模块": []})
        self.assertTrue(ws.视图md.is_file())
        self.assertTrue(ws.视图json.is_file())

    def test_空图不再要领域名(self):
        """领域自格式版本 2 起不是图的字段（ADR-0023）：--name 连参数都没有。"""
        r = 工.跑引擎("--graph", self.tmp / "别的.json", "init", "--empty", "--name", "菜园")
        self.assertEqual(r.code, 2, r)

    def test_整份拷入带来构成模板时限与稳定id(self):
        ws = self.整份工作区()
        self.assertEqual(ws.模块标题(), ["整地", "播种", "养护", "收获"])
        self.assertEqual(ws.节点标题("养护"), ["浇水", "除草", "搭架"])
        n = ws.节点("施底肥")
        self.assertEqual(n["id"], "n-1-2", "预设图的 id 原样带过来，别处按 id 认它")
        self.assertEqual(n["空白模板"], "施肥记录.docx")
        self.assertEqual(n["时限"], "自松土完成之日起 3 日内（手册，示例）", "时限句随起手拷入")
        self.assertEqual(n["条目"], [])
        self.assertNotIn("时限", ws.节点("松土"), "预设图里没时限的节点不凭空长一个")
        for m in ws.读图()["模块"]:
            for x in m["节点"]:
                self.assertEqual(x["条目"], [])

    def test_整份拷入收目录也收文件(self):
        目录 = self.预设图()
        ws = 工.起工作区(self.tmp / "甲", 预设图=目录)
        self.assertEqual(ws.模块标题(), ["整地", "播种", "养护", "收获"])
        (self.tmp / "乙").mkdir()
        r = 工.跑引擎("--graph", self.tmp / "乙" / "图.json", "init",
                      "--preset", 目录 / graph.PRESET_FILENAME)
        self.assertEqual(r.code, 0, r)

    def test_案件图上律师仍不能写时限(self):
        """时限来源从运行时查预设图改成起手拷入，但案件图上写它照旧拒（ADR-0016、ADR-0023）。"""
        ws = self.整份工作区()
        r = self.rejected(ws, "set-time-limit", "--node", "松土", "--time-limit", "三日内")
        self.assertIn("时限", r.err)
        self.rejected(ws, "add-node", "--module", "整地", "--title", "翻晒", "--time-limit", "三日内")
        self.assertEqual(ws.节点标题("整地"), ["松土", "施底肥"], "拒了就一个字都不落")

    def test_旧的起手参数都是用法错(self):
        """--full、--from、--domain 删了（ADR-0023）：传了就是用法错，不是静默忽略。"""
        for 参数 in (["init", "--full"], ["init", "--from", "x.json"],
                     ["--domain", "x", "init", "--empty"], ["--kind", "domain", "init", "--empty"]):
            r = 工.跑引擎("--graph", self.tmp / "新.json", *参数)
            self.assertEqual(r.code, 2, "%s 该是用法错：%r" % (参数, r))

    def test_起手二选一给零个或两个都拒(self):
        for 参数 in ([], ["--empty", "--preset", str(self.预设图())]):
            r = 工.跑引擎("--graph", self.tmp / "新.json", "init", *参数)
            self.assertEqual(r.code, 1, r)
            self.assertIn("二选一", r.err)

    def test_图已存在就不再起手(self):
        ws = self.空图工作区()
        self.rejected(ws, "init", "--empty")

    def test_预设图不合校验时案件图不落盘(self):
        坏 = self.tmp / "坏预设图"
        坏.mkdir()
        (坏 / graph.PRESET_FILENAME).write_text('{"格式版本": 2}', encoding="utf-8")
        目标 = self.tmp / "案件" / "图.json"
        r = 工.跑引擎("--graph", 目标, "init", "--preset", 坏)
        self.assertEqual(r.code, 1, r)
        self.assertIn("预设图不合校验", r.err)
        self.assertFalse(目标.exists())


# ---------------------------------------------------------------- 校验

class ValidationTest(EngineCase):
    def 写原样(self, ws, obj):
        import json
        ws.图.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_不合校验即拒且文件一字不动(self):
        ws = self.空图工作区()
        raw = ws.读图()
        raw["状态"] = "乱写"
        self.写原样(ws, raw)
        before = ws.图.read_bytes()
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("不合校验", r.err)
        self.assertEqual(ws.图.read_bytes(), before)

    def test_顶层还带领域即拒并指出原因(self):
        ws = self.空图工作区()
        raw = ws.读图()
        raw["领域"] = "菜园"
        self.写原样(ws, raw)
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("领域", r.err)
        self.assertIn("领域自格式版本 2 起不是图的字段", r.err)

    def test_空白模板的旧写法即拒(self):
        ws = self.整份工作区()
        raw = ws.读图()
        raw["模块"][0]["节点"][1]["空白模板"] = {"来源": "官方", "文件": "施肥记录.docx"}
        self.写原样(ws, raw)
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("旧写法", r.err)
        self.rejected(ws, "set-template", "--node", "松土", "--template", "官方:x.docx")

    def test_空白模板只收文件名不收路径(self):
        ws = self.整份工作区()
        r = self.rejected(ws, "set-template", "--node", "松土", "--template", "模板/x.docx")
        self.assertIn("不带路径", r.err)

    def test_生成条目还带源即拒(self):
        ws = self.整份工作区()
        ws.出一版("整地", "松土")
        raw = ws.读图()
        raw["模块"][0]["节点"][0]["条目"][0]["源"] = "文书/松土/松土.md"
        self.写原样(ws, raw)
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("源", r.err)
        r = 工.跑引擎("--graph", ws.图, "generate", "--node", "松土", "--doc", "a.docx",
                      "--review", "b.md", "--source", "c.md")
        self.assertEqual(r.code, 2, "--source 删了，传了就是用法错：%r" % r)

    def test_格式版本不认识即拒(self):
        ws = self.空图工作区()
        self.写原样(ws, {"格式版本": 99, "模块": []})
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("格式版本", r.err)

    def test_格式版本1的图先报版本不对(self):
        """旧版本的图字段本来就不一样；先报「顶层多了个 领域」会把人引到错的地方。"""
        ws = self.空图工作区()
        self.写原样(ws, {"格式版本": 1, "领域": "菜园", "模块": []})
        r = self.rejected(ws, "add-module", "--title", "甲")
        self.assertIn("本引擎只认 2", r.err)
        self.assertIn("重新起手", r.err)

    def test_不是JSON即拒(self):
        ws = self.空图工作区()
        ws.图.write_text("{oops", encoding="utf-8")
        self.rejected(ws, "add-module", "--title", "甲")

    def test_标题重复即拒(self):
        ws = self.整份工作区()
        raw = ws.读图()
        raw["模块"][0]["节点"][1]["标题"] = "松土"
        self.写原样(ws, raw)
        self.rejected(ws, "add-module", "--title", "甲")

    def test_validate子命令(self):
        ws = self.整份工作区()
        self.assertEqual(ws.调("validate").code, 0)
        self.写原样(ws, {"格式版本": 2})
        self.assertEqual(ws.调("validate").code, 1)

    def test_图不在即拒(self):
        r = 工.跑引擎("--graph", self.tmp / "没有的" / "图.json", "add-module", "--title", "甲")
        self.assertEqual(r.code, 1, r)
        self.assertIn("图.json", r.err)


if __name__ == "__main__":
    unittest.main()
