"""入库（#103 验收，ADR-0020）：sketch.py intake 的规矩。

运行：python -m unittest tests/domain/test_intake.py

缝与 test_home.py 同一条：intake 这一条命令加两个临时根（活图根、种子根），种子根里摆一个假 `.git`
充当「在仓库里」。任何一个测试都不碰真的 ~/.loo0ng，也不碰仓库里真的 assets/。
领域用合成小领域「菜园」，没有案件内容。

本票的重点断言是「回显把新增与改名分开列出」：入库是整份送进去，那几行是隐私钩子与第二双眼之前的
第一道人眼过滤（ADR-0020）。
"""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "engineering" / "domain" / "scripts" / "sketch.py"
菜园 = REPO / "evals" / "领域" / "菜园"

spec = importlib.util.spec_from_file_location("loo0ng_sketch_intake", SCRIPT)
sketch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sketch)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="intake-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.live_root = self.tmp / "活图家" / "领域"
        self.seed_root = self.tmp / "假仓库" / "skills" / "engineering" / "domain" / "assets"
        (self.tmp / "假仓库" / ".git").mkdir(parents=True)   # 「在仓库里」的判据
        self.seed_root.mkdir(parents=True)
        self.live = self.live_root / "菜园"
        self.live.mkdir(parents=True)
        shutil.copy2(菜园 / "领域图.json", self.live / "领域图.json")
        self.seed = self.seed_root / "菜园" / "领域图.json"

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sketch.main(list(argv))
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 2
        return Run(code, out.getvalue(), err.getvalue())

    def intake(self, name="菜园"):
        return self.cli("intake", "--name", name,
                        "--live-root", str(self.live_root), "--seed-root", str(self.seed_root))

    def 改活图(self, fn):
        path = self.live / "领域图.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def 种子(self):
        return json.loads(self.seed.read_text(encoding="utf-8"))


class 第一次入库(Base):
    def test_种子里还没有就整份放进去(self):
        r = self.intake()
        self.assertEqual(r.code, 0, r)
        self.assertTrue(self.seed.is_file(), "种子没落盘：%r" % r)
        self.assertEqual(self.seed.read_bytes(), (self.live / "领域图.json").read_bytes(),
                         "入库该是活图那份的逐字副本")
        self.assertIn("第一次入库", r.out)

    def test_回显逐条点名新增(self):
        r = self.intake()
        self.assertIn("新增模块", r.out)
        self.assertIn("新增节点", r.out)
        self.assertIn("「松土」", r.out, "新增的节点要逐条点名：%r" % r.out)

    def test_只拿领域图不拿整个领域目录(self):
        """硬边界 1 最不想要的形状是整份拷：活图目录下的任何东西都别卷进仓库（ADR-0020）。"""
        (self.live / "模板").mkdir()
        (self.live / "模板" / "施肥记录.docx").write_bytes(b"synthetic-template")
        (self.live / "指引手册").mkdir()
        (self.live / "指引手册" / "种菜手册.docx").write_bytes(b"synthetic-handbook")
        (self.live / "办案时随手记的.md").write_text("案件内容", encoding="utf-8")
        r = self.intake()
        self.assertEqual(r.code, 0, r)
        剩下 = sorted(p.name for p in (self.seed_root / "菜园").iterdir())
        self.assertEqual(剩下, ["领域图.json"], "种子目录里多了东西：%s" % 剩下)


class 回显把新增与改名分开(Base):
    """本票的重点：整份送进去，第二双眼要审的 diff 一下子变大，回显得先把它分栏摊开。"""

    def setUp(self):
        super().setUp()
        self.assertEqual(self.intake().code, 0, "前置：先入一次库当种子")

        def 改(data):
            mods = {m["id"]: m for m in data["模块"]}
            for n in mods["m-yanghu"]["节点"]:
                if n["id"] == "n-jiaoshui":
                    n["标题"] = "浇灌"                                   # 改名
                if n["id"] == "n-chucao":
                    n["空白模板"] = {"来源": "官方", "文件": "除草记录.docx"}  # 改属性
            data["模块"].append({"id": "m-yuedong", "标题": "越冬", "节点": [      # 新增模块
                {"id": "n-fumo", "标题": "覆膜", "空白模板": "无", "条目": []}]})  # 新增节点
        self.改活图(改)
        self.r = self.intake()

    def test_跑得通(self):
        self.assertEqual(self.r.code, 0, self.r)

    def test_摘要一行数得出多了几个改了几个(self):
        self.assertIn("多了 1 个模块、1 个节点", self.r.out, "摘要那一行没数对：%r" % self.r.out)
        self.assertIn("改了 1 个标题", self.r.out)

    def test_新增与改名各占一栏且不混在一起(self):
        行 = self.r.out.splitlines()
        新增栏 = [i for i, x in enumerate(行) if x.startswith("新增节点（")]
        改名栏 = [i for i, x in enumerate(行) if x.startswith("改名（")]
        self.assertEqual(len(新增栏), 1, "新增该恰好一栏：%r" % self.r.out)
        self.assertEqual(len(改名栏), 1, "改名该恰好一栏：%r" % self.r.out)
        新增 = 行[新增栏[0] + 1]
        改名 = 行[改名栏[0] + 1]
        self.assertIn("覆膜", 新增)
        self.assertNotIn("浇灌", 新增, "改名的混进了新增栏：%r" % 新增)
        self.assertIn("「浇水」→「浇灌」", 改名, "改名要写清改前改后：%r" % 改名)
        self.assertNotIn("覆膜", 改名, "新增的混进了改名栏：%r" % 改名)

    def test_改属性另算一栏不算改名(self):
        self.assertIn("改属性（1）", self.r.out)
        self.assertIn("官方 除草记录.docx", self.r.out)

    def test_种子跟着改了(self):
        titles = [n["标题"] for m in self.种子()["模块"] for n in m["节点"]]
        self.assertIn("浇灌", titles)
        self.assertIn("覆膜", titles)


class 拷之前先拦住(Base):
    def test_活图不合校验就拒且种子一个字不改(self):
        self.assertEqual(self.intake().code, 0)
        原样 = self.seed.read_bytes()
        self.改活图(lambda d: d["模块"][0]["节点"][0].update(
            {"条目": [{"动作": "生成", "时间": "2026-09-11T00:00:00+08:00", "文书": "x.md",
                       "审查报告": "y.md", "来源": "agent"}]}))
        r = self.intake()
        self.assertEqual(r.code, 1, r)
        self.assertIn("不合校验", r.err)
        self.assertEqual(self.seed.read_bytes(), 原样, "拒了还是把种子改了")

    def test_领域名对不上就拒(self):
        self.改活图(lambda d: d.update({"领域": "果园"}))
        r = self.intake()
        self.assertEqual(r.code, 1, r)
        self.assertIn("对不上", r.err)
        self.assertFalse(self.seed.exists(), "拒了还是落了盘")

    def test_找不到活图就拒(self):
        r = self.intake("没有这个领域")
        self.assertEqual(r.code, 1, r)
        self.assertIn("找不到活图", r.err)

    def test_种子根不在git工作树里就拒(self):
        """入库只在仓库里做：装好的那份 skill 包里写种子，下一次升级就被整个换掉。"""
        shutil.rmtree(self.tmp / "假仓库" / ".git")
        r = self.intake()
        self.assertEqual(r.code, 1, r)
        self.assertIn("只在本仓库里做", r.err)
        self.assertFalse(self.seed.exists())

    def test_领域名不能带路径分隔符(self):
        for bad in ("../外面", "菜园/模板", "a\\b", ".", ""):
            r = self.intake(bad)
            self.assertEqual(r.code, 1, "%r 应被拒：%r" % (bad, r))


class 没有要入库的(Base):
    def test_逐字相同就不拷(self):
        self.assertEqual(self.intake().code, 0)
        os.utime(self.seed, (1000000000, 1000000000))
        mtime = self.seed.stat().st_mtime
        r = self.intake()
        self.assertEqual(r.code, 0, r)
        self.assertIn("一个字没拷", r.out)
        self.assertEqual(self.seed.stat().st_mtime, mtime, "逐字相同还是拷了一遍")


class 种子里有活图里没有(Base):
    def test_单列一栏并说清入库之后就没了(self):
        self.assertEqual(self.intake().code, 0)
        self.改活图(lambda d: d["模块"].pop())
        r = self.intake()
        self.assertEqual(r.code, 0, r)
        self.assertIn("种子里有、活图里没有", r.out)
        self.assertIn("「收获」", r.out)
        self.assertNotIn("收获", [m["标题"] for m in self.种子()["模块"]])


if __name__ == "__main__":
    unittest.main()
