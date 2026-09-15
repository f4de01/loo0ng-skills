"""skills/in-progress/domain/scripts/sketch.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/domain/test_sketch.py

缝是雏形 CLI 加一张图：每个测试在临时目录里调 main(argv)，再读回显与图断言。图与预设图都由
tests/共用/工作区.py 用引擎自己造（#12），领域是合成小领域「菜园」：雏形机制不认破产语义（ADR-0015）。
写入一律经图引擎子进程（雏形不是第二个写入口）。

判重只剩同名这一半（ADR-0024）：相似不同名由模型对着 check 末尾那份「图里现有的标题」自己判，
脚本里没有相似度、没有阈值、没有「待定」。下面几条断言就钉这件事。
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "in-progress" / "domain" / "scripts" / "sketch.py"

sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

spec = importlib.util.spec_from_file_location("loo0ng_sketch", SCRIPT)
sketch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sketch)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class SketchCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="sketch-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.源 = 工.造预设图(self.tmp / "源", 名="菜园")
        self.ws = 工.起工作区(self.tmp / "ws", 预设图=self.源)
        self.proposal_path = self.tmp / "雏形.json"

    # ---- 造件
    def 写雏形(self, 模块, path=None, **extra):
        data = {"模块": 模块}
        data.update(extra)
        (path or self.proposal_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path or self.proposal_path

    def 空预设图(self, 名="新的"):
        目录 = self.tmp / "个人" / 名
        目录.mkdir(parents=True)
        图 = 目录 / "预设图.json"
        工.跑引擎("--graph", 图, "--kind", "preset", "init", "--empty", 须过=True)
        return 图

    # ---- 跑
    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sketch.main([str(a) for a in argv])
            except SystemExit as e:  # argparse 的用法错误
                code = e.code
        return Run(code, out.getvalue(), err.getvalue())

    def check(self, *argv, **kw):
        return self.cli("check", "--proposal", self.proposal_path, "--graph", kw.get("graph", self.ws.图),
                        *argv)

    def apply(self, *argv, **kw):
        return self.cli("apply", "--proposal", self.proposal_path, "--graph", kw.get("graph", self.ws.图),
                        *argv)

    def 读(self, 图=None):
        return json.loads(pathlib.Path(图 or self.ws.图).read_text(encoding="utf-8"))

    def 标题表(self, 图=None):
        return {m["标题"]: [n["标题"] for n in m["节点"]] for m in self.读(图)["模块"]}


class 判同名(SketchCase):
    def test_check_不写图(self):
        before = self.ws.图.read_bytes()
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.check()
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.ws.图.read_bytes(), before, "check 只读")
        self.assertIn("拍板前 图.json 一字未动", r.out)

    def test_同名的挑掉不重复提出(self):
        self.写雏形([{"标题": "养护", "节点": [{"标题": "浇水", "空白模板": "无"},
                                              {"标题": "施追肥", "空白模板": "无"}]}])
        r = self.check()
        self.assertIn("## 已在图里，不重复提出（同名）", r.out)
        self.assertIn("节点「浇水」（图里在模块「养护」下）", r.out)
        新提出 = r.out.split("## 新提出")[1].split("##")[0]
        self.assertIn("施追肥", 新提出)
        self.assertNotIn("节点「浇水」：", 新提出)

    def test_同名只看归一化后的标题(self):
        self.写雏形([{"标题": "养护", "节点": [{"标题": " 浇 水 ", "空白模板": "无"}]}])
        r = self.check()
        self.assertIn("已在图里", r.out, "不计空白、标点、全半角")

    def test_相似不同名脚本不判待定(self):
        self.写雏形([{"标题": "整地", "节点": [{"标题": "施足底肥", "空白模板": "无"}]}])
        r = self.check()
        self.assertEqual(r.code, 0, r)
        self.assertNotIn("待定", r.out, "像不像归模型（ADR-0024），脚本不出这个状态")
        self.assertIn("施足底肥", r.out.split("## 新提出")[1].split("##")[0], "不同名就是新提出")

    def test_回显末尾打出图里现有的标题(self):
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.check()
        清单 = r.out.split("## 图里现有的标题（判相似用）")[1]
        for 标题 in ("整地", "播种", "养护", "收获"):
            self.assertIn(标题, 清单.split("节点：")[0])
        for 标题 in ("松土", "施底肥", "浇水", "记账"):
            self.assertIn(标题, 清单.split("节点：")[1])
        self.assertIn("判成同一个就把那条从雏形文件里删掉", 清单)

    def test_空图上现有标题写无(self):
        空 = 工.起工作区(self.tmp / "空ws")
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.check(graph=空.图)
        self.assertIn("模块：（无）", r.out)
        self.assertIn("节点：（无）", r.out)


class 写入(SketchCase):
    def test_apply_逐条经引擎写入(self):
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "施肥记录.docx"},
                                              {"标题": "清园", "空白模板": "无"}]},
                     {"标题": "养护", "节点": [{"标题": "施追肥", "空白模板": "无"}]}],
                   来源="参考/指南/种植指南.md")
        r = self.apply()
        self.assertEqual(r.code, 0, r)
        表 = self.标题表()
        self.assertEqual(表["越冬"], ["覆膜", "清园"], "数组顺序即顺序，新模块追加在末尾")
        self.assertEqual(表["养护"], ["浇水", "除草", "搭架", "施追肥"], "同名模块下追加，不新建一个模块")
        self.assertIn("已新增模块「越冬」", r.out, "引擎的回显照抄")
        self.assertEqual(self.ws.节点("覆膜")["空白模板"], "施肥记录.docx")

    def test_写完重算两份视图(self):
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        self.assertEqual(self.apply().code, 0)
        self.assertIn("覆膜", self.ws.读视图文())
        self.assertEqual(self.ws.视图节点("覆膜")["状态"], "未生成")

    def test_全同名时什么都不写(self):
        before = self.ws.图.read_bytes()
        self.写雏形([{"标题": "养护", "节点": [{"标题": "浇水", "空白模板": "无"}]}])
        r = self.apply()
        self.assertEqual(r.code, 0, r)
        self.assertIn("没有要写的", r.out)
        self.assertEqual(self.ws.图.read_bytes(), before)

    def test_案件图上时限只回显不写(self):
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无",
                                              "时限": "自霜降之日起 5 日内（指南，示例）"}]}])
        r = self.check()
        self.assertIn("自霜降之日起 5 日内", r.out)
        self.assertIn("时限只回显、案件图不存", r.out)
        r = self.apply()
        self.assertEqual(r.code, 0, r)
        self.assertNotIn("时限", self.ws.节点("覆膜"))
        self.assertIn("时限句没有写进案件图", r.out)

    def test_案件图上给了id即拒一字不写(self):
        before = self.ws.图.read_bytes()
        self.写雏形([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无", "id": "n-fumo"}]}])
        r = self.apply()
        self.assertEqual(r.code, 1, r)
        self.assertIn("id 由引擎生成", r.err)
        self.assertEqual(self.ws.图.read_bytes(), before)

    def test_预设图收id与时限(self):
        图 = self.空预设图()
        self.写雏形([{"标题": "整地", "id": "m-zheng", "节点": [
            {"标题": "松土", "空白模板": "无", "id": "n-song", "时限": "自立春之日起 3 日内（手册，示例）"}]}])
        r = self.apply("--kind", "preset", graph=图)
        self.assertEqual(r.code, 0, r)
        节点 = self.读(图)["模块"][0]["节点"][0]
        self.assertEqual((节点["id"], 节点["时限"]), ("n-song", "自立春之日起 3 日内（手册，示例）"))
        self.assertEqual(self.读(图)["模块"][0]["id"], "m-zheng")

    def test_引擎拒了哪条就报哪条其余照写(self):
        图 = self.空预设图()
        self.写雏形([{"标题": "整地", "id": "m-zheng", "节点": [
            {"标题": "松土", "空白模板": "无", "id": "n-same"},
            {"标题": "耙地", "空白模板": "无", "id": "n-same"}]}])
        r = self.apply("--kind", "preset", graph=图)
        self.assertEqual(r.code, 1, r)
        self.assertIn("耙地", r.err)
        self.assertEqual([n["标题"] for n in self.读(图)["模块"][0]["节点"]], ["松土"], "其余照写")

    def test_预设图回显说的是预设图(self):
        图 = self.空预设图()
        self.写雏形([{"标题": "整地", "节点": [{"标题": "松土", "空白模板": "无"}]}])
        r = self.check("--kind", "preset", graph=图)
        self.assertIn("预设图）", r.out.splitlines()[0])


class 雏形不合格式(SketchCase):
    def 拒(self, 模块, 片段, **extra):
        before = self.ws.图.read_bytes()
        self.写雏形(模块, **extra)
        for r in (self.check(), self.apply()):
            self.assertEqual(r.code, 1, r)
            self.assertIn(片段, r.err)
        self.assertEqual(self.ws.图.read_bytes(), before, "拒了就一字不写")

    def test_缺键(self):
        self.拒([{"标题": "越冬"}], "须有 标题 与 节点")

    def test_节点缺空白模板(self):
        self.拒([{"标题": "越冬", "节点": [{"标题": "覆膜"}]}], "须有 标题 与 空白模板")

    def test_标题为空(self):
        self.拒([{"标题": "  ", "节点": []}], "非空字符串")

    def test_空白模板带路径(self):
        self.拒([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "模板/覆膜.docx"}]}], "只写文件名")

    def test_空白模板还是旧的来源加文件写法(self):
        self.拒([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "官方:覆膜.docx"}]}], "只写文件名")

    def test_雏形内部同名(self):
        self.拒([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"},
                                          {"标题": "覆 膜", "空白模板": "无"}]}], "同名")

    def test_顶层多了键(self):
        self.拒([{"标题": "越冬", "节点": []}], "顶层键", 时限="不该在这里")

    def test_找不到雏形文件(self):
        r = self.cli("check", "--proposal", self.tmp / "没有这个.json", "--graph", self.ws.图)
        self.assertEqual(r.code, 1, r)
        self.assertIn("找不到雏形文件", r.err)

    def test_找不到图(self):
        self.写雏形([{"标题": "越冬", "节点": []}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.tmp / "没有图.json")
        self.assertEqual(r.code, 1, r)
        self.assertIn("找不到图", r.err)


class 命令面(SketchCase):
    def test_只有两个子命令(self):
        for 退场 in ("home", "intake", "from-case", "docx-text"):
            r = self.cli(退场, "--name", "菜园")
            self.assertEqual(r.code, 2, "%s 随 ADR-0023 退场，不该还在 CLI 上：%r" % (退场, r))

    def test_没有子命令即用法错(self):
        self.assertEqual(self.cli().code, 2)


if __name__ == "__main__":
    unittest.main()
