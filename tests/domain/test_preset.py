"""skills/in-progress/domain/scripts/preset.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/domain/test_preset.py

缝是两处预设图加一个案件工作区：每个测试在临时目录里调 main(argv)，再读回显与落盘的文件断言。
两处的根一律用 --factory-root / --personal-root 指进临时目录，**任何一条都不碰真的 ~/.loo0ng**
（ADR-0015 只生不存）。工作区与预设图都由 tests/共用/工作区.py 用引擎自己造（#12），
领域是合成小领域「菜园」：本 skill 不认任何领域语义，测试也不拿破产那份来测机制。
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
SCRIPT = REPO / "skills" / "in-progress" / "domain" / "scripts" / "preset.py"

sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

spec = importlib.util.spec_from_file_location("loo0ng_preset", SCRIPT)
preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class PresetCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="preset-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.出厂 = self.tmp / "出厂"
        self.个人 = self.tmp / "个人"
        self.出厂.mkdir()
        self.个人.mkdir()

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = preset.main([str(a) for a in argv] + ["--factory-root", str(self.出厂),
                                                             "--personal-root", str(self.个人)])
            except SystemExit as e:  # argparse 的用法错误
                code = e.code
        return Run(code, out.getvalue(), err.getvalue())

    def 造一份(self, 根, 名, 模块=None):
        return 工.造预设图(根, 模块 if 模块 is not None else 工.菜园, 名=名)

    def 起工作区(self, 预设图=None):
        return 工.起工作区(self.tmp / "ws", 预设图=预设图)


class 列表(PresetCase):
    def test_两组各自回显(self):
        self.造一份(self.出厂, "菜园")
        self.造一份(self.个人, "菜园3.0")
        r = self.cli("list")
        self.assertEqual(r.code, 0, r)
        self.assertIn("出厂（%s）：" % self.出厂.as_posix(), r.out)
        self.assertIn("个人（%s）：" % self.个人.as_posix(), r.out)
        self.assertIn("- 菜园：4 个模块、9 个节点，模板 2 件", r.out)
        self.assertIn("- 菜园3.0：", r.out)
        self.assertLess(r.out.index("出厂（"), r.out.index("个人（"), "出厂那组排在前面")

    def test_一组空写无(self):
        self.造一份(self.出厂, "菜园")
        r = self.cli("list")
        self.assertEqual(r.code, 0, r)
        self.assertIn("- （无）", r.out)

    def test_两处都空也退零(self):
        r = self.cli("list")
        self.assertEqual(r.code, 0, r)
        self.assertIn("只能从空图起手", r.out)

    def test_不是预设图的目录不列(self):
        (self.个人 / "随手建的").mkdir()
        (self.个人 / "随手建的" / "笔记.md").write_text("不是预设图\n", encoding="utf-8")
        r = self.cli("list")
        self.assertNotIn("随手建的", r.out, "没有 预设图.json 的目录不算一份预设图")

    def test_坏图只在它那一行说读不出(self):
        好 = self.造一份(self.个人, "好的")
        坏 = self.个人 / "坏的"
        坏.mkdir()
        (坏 / "预设图.json").write_text("{不是 JSON", encoding="utf-8")
        r = self.cli("list")
        self.assertEqual(r.code, 0, "一份坏图不该让整条命令拒")
        self.assertIn("- 坏的：读不出", r.out)
        self.assertIn("- 好的：4 个模块", r.out)
        self.assertTrue((好 / "预设图.json").is_file())


class 解析(PresetCase):
    def test_出厂与个人各回绝对路径(self):
        f = self.造一份(self.出厂, "菜园")
        p = self.造一份(self.个人, "菜园3.0")
        r = self.cli("resolve", "--name", "菜园", "--owner", "出厂")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out.splitlines()[0], f.as_posix())
        r = self.cli("resolve", "--name", "菜园3.0", "--owner", "个人")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out.splitlines()[0], p.as_posix())

    def test_两处都没有即拒(self):
        r = self.cli("resolve", "--name", "没有这个", "--owner", "个人")
        self.assertEqual(r.code, 1, r)
        self.assertIn("没有这个", r.err)
        self.assertIn("从空图起手", r.err)

    def test_名在另一归属下时点出来不回退(self):
        self.造一份(self.出厂, "菜园")
        r = self.cli("resolve", "--name", "菜园", "--owner", "个人")
        self.assertEqual(r.code, 1, "不猜、不回退到另一个归属")
        self.assertIn("出厂", r.err)
        self.assertIn("--owner", r.err)

    def test_目录在但没有预设图也拒(self):
        (self.个人 / "空壳").mkdir()
        r = self.cli("resolve", "--name", "空壳", "--owner", "个人")
        self.assertEqual(r.code, 1, r)

    def test_名带路径分隔符即拒(self):
        for 名 in ("..", "a/b", "a\\b"):
            r = self.cli("resolve", "--name", 名, "--owner", "个人")
            self.assertEqual(r.code, 1, (名, r))
            self.assertIn("目录名", r.err)

    def test_归属只有两个值(self):
        r = self.cli("resolve", "--name", "菜园", "--owner", "出厂预设图")
        self.assertEqual(r.code, 2, "用法错误退 2")


class 另存(PresetCase):
    def setUp(self):
        super().setUp()
        self.源 = self.造一份(self.tmp / "源", "菜园")
        self.ws = self.起工作区(self.源)
        self.ws.出一版("整地", "松土")
        self.ws.调("confirm", "--node", "松土", "--words", "确认松土", 须过=True)
        self.ws.调("not-applicable", "--node", "除草", "--words", "今年不除草", 须过=True)
        self.图字节 = self.ws.图.read_bytes()

    def 另存(self, 名="菜园3.0"):
        return self.cli("save", "--name", 名, "--graph", self.ws.图, "--templates", self.ws.模板)

    def test_产物只剩构成案件图一字不动(self):
        r = self.另存()
        self.assertEqual(r.code, 0, r)
        存 = self.个人 / "菜园3.0"
        data = json.loads((存 / "预设图.json").read_text(encoding="utf-8"))
        self.assertEqual(data["格式版本"], 2)
        self.assertEqual(sorted(data), ["格式版本", "模块"], "顶层不带 领域")
        self.assertEqual([m["标题"] for m in data["模块"]], [m for m, _ in 工.菜园])
        for m in data["模块"]:
            for n in m["节点"]:
                self.assertEqual(n["条目"], [], "条目与不适用记录都剥掉")
        self.assertEqual(self.ws.图.read_bytes(), self.图字节, "案件图一字不动")

    def test_时限与空白模板随构成留下(self):
        self.assertEqual(self.另存().code, 0)
        data = json.loads((self.个人 / "菜园3.0" / "预设图.json").read_text(encoding="utf-8"))
        节点 = {n["标题"]: n for m in data["模块"] for n in m["节点"]}
        self.assertEqual(节点["施底肥"]["空白模板"], "施肥记录.docx")
        self.assertIn("时限", 节点["施底肥"])
        self.assertNotIn("时限", 节点["松土"])

    def test_模板整份拷进去(self):
        (self.ws.模板 / "律师自己的.docx").write_bytes((self.ws.模板 / "施肥记录.docx").read_bytes())
        r = self.另存()
        self.assertEqual(r.code, 0, r)
        拷到 = self.个人 / "菜园3.0" / "模板"
        self.assertEqual(sorted(p.name for p in 拷到.glob("*")),
                         sorted(["播种登记.docx", "律师自己的.docx", "施肥记录.docx"]))
        self.assertEqual((拷到 / "施肥记录.docx").read_bytes(), (self.ws.模板 / "施肥记录.docx").read_bytes(),
                         "拷贝逐字节相同，不改名")
        self.assertIn("模板拷了 3 件", r.out)

    def test_与出厂重名即拒且什么都没落(self):
        self.造一份(self.出厂, "菜园3.0")
        r = self.另存()
        self.assertEqual(r.code, 1, r)
        self.assertIn("出厂", r.err)
        self.assertEqual(list(self.个人.iterdir()), [], "拒了就一个字不写")

    def test_出厂那个名被占着就算图读不出也拒(self):
        (self.出厂 / "菜园3.0").mkdir()          # 目录在、预设图.json 还没有：名占着就是占着
        r = self.另存()
        self.assertEqual(r.code, 1, r)
        self.assertIn("出厂", r.err)
        self.assertEqual(list(self.个人.iterdir()), [])

    def test_目标已存在不覆盖(self):
        旧 = self.造一份(self.个人, "菜园3.0", 模块=[("旧的", [("旧节点", None, None)])])
        旧字节 = (旧 / "预设图.json").read_bytes()
        r = self.另存()
        self.assertEqual(r.code, 1, r)
        self.assertIn("不覆盖", r.err)
        self.assertEqual((旧 / "预设图.json").read_bytes(), 旧字节, "旧的那份一字不动")

    def test_名不合法即拒(self):
        r = self.另存("../跑出去")
        self.assertEqual(r.code, 1, r)
        self.assertIn("目录名", r.err)

    def test_工作区没有模板目录也存得下(self):
        shutil.rmtree(str(self.ws.模板))
        r = self.另存()
        self.assertEqual(r.code, 0, r)
        self.assertIn("一件模板没拷", r.out)
        self.assertTrue((self.个人 / "菜园3.0" / "预设图.json").is_file())

    def test_案件图读不出即拒不留半份(self):
        self.ws.图.write_text("{不是 JSON", encoding="utf-8")
        r = self.另存()
        self.assertEqual(r.code, 1, r)
        self.assertEqual(list(self.个人.iterdir()), [], "落一半不留半份预设图")

    def test_找不到案件图即拒(self):
        r = self.cli("save", "--name", "菜园3.0", "--graph", self.tmp / "没有这个" / "图.json",
                     "--templates", self.ws.模板)
        self.assertEqual(r.code, 1, r)
        self.assertIn("案件工作区", r.err)

    def test_另存出来的能整份起手回去(self):
        self.assertEqual(self.另存().code, 0)
        回 = 工.起工作区(self.tmp / "ws2", 预设图=self.个人 / "菜园3.0")
        self.assertEqual(回.模块标题(), [m for m, _ in 工.菜园])
        self.assertEqual(回.节点("松土")["条目"], [], "起手回来的图没有上一个案子的条目")
        self.assertEqual(sorted(p.name for p in 回.模板.glob("*")), ["播种登记.docx", "施肥记录.docx"])


if __name__ == "__main__":
    unittest.main()
