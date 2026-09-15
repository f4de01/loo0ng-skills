"""包内出厂预设图谁都不许写（#99 验收，ADR-0020；路径按 ADR-0023 换成预设图的形状）。

运行：python -m unittest tests/graph/test_package_guard.py

挡的是这条路：律师或开发者把累计下来的图写进包内那份，而它下一次 skill 包升级就被整个换掉，
静默丢失，律师这一侧没有 git 看得见。律师要复用整案的图走另存（`export-preset`）落到个人
预设图；开发者要改出厂件也是先写个人预设图，再经 PR 进仓库。所以这条拒**没有放行口**，
引擎里也就没有例外分支。

两条判据取或：
  ①（真包）按 graph.py 自己的位置算出的兄弟 skill assets/预设图/，装在哪儿都成立
  ②（假包）目录名摆成 <...>/assets/预设图/<名>，别处拷来的一份包

**拒的行为一律拿 ② 造的临时假包测**：拿真包测就是拿开发者的工作树赌一次规则，规则坏了它会被
写脏。真包这一侧只留一条只读断言，钉住判据 ① 算出来的就是仓库里那个目录。
"""
import json
import pathlib
import shutil
import subprocess
import tempfile
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

graph = 工.引擎
SCRIPT = 工.引擎脚本
真包 = REPO / "skills" / "engineering" / "domain" / "assets" / "预设图"


def cli(*argv):
    r = subprocess.run([sys.executable, str(SCRIPT)] + [str(a) for a in argv],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="pkgguard-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # 判据 ②：一份摆成 <...>/assets/预设图/<名> 的假包
        源 = 工.造预设图(self.tmp / "源", 名="菜园")
        self.假出厂 = self.tmp / "domain" / "assets" / "预设图" / "菜园"
        shutil.copytree(str(源), str(self.假出厂))
        self.出厂图 = self.假出厂 / graph.PRESET_FILENAME
        # 包外的个人预设图，同样内容：每条「拒」都配一条「个人那份上照做」，证明拒的是位置不是操作
        self.个人 = self.tmp / "loo0ng" / "预设图" / "菜园"
        shutil.copytree(str(源), str(self.个人))
        self.个人图 = self.个人 / graph.PRESET_FILENAME

    def 字节(self, p):
        return pathlib.Path(p).read_bytes()


class 写包内即拒Case(Base):
    """出厂件上的每一种写都拒，且文件一个字节不动。"""

    def 拒(self, *argv):
        before = self.字节(self.出厂图)
        code, out = cli("--graph", self.出厂图, "--kind", "preset", *argv)
        self.assertEqual(code, 1, "写包内出厂件该拒，实际过了：%s" % out)
        self.assertIn("ADR-0020", out, "拒绝消息该点到裁定的出处：%s" % out)
        self.assertEqual(self.字节(self.出厂图), before, "拒了却动了文件：引擎拒写时文件一字不动")
        return out

    def test_add_node被拒(self):
        self.拒("add-node", "--module", "养护", "--title", "补种记录", "--id", "n-buzhong")

    def test_add_module被拒(self):
        self.拒("add-module", "--title", "新模块", "--id", "m-xin")

    def test_rename_node被拒(self):
        self.拒("rename-node", "--node", "除草", "--title", "除草与松土")

    def test_move_node被拒(self):
        self.拒("move-node", "--node", "除草", "--first")

    def test_set_time_limit被拒(self):
        self.拒("set-time-limit", "--node", "除草", "--time-limit", "七日内（示例）")

    def test_init起手也被拒(self):
        """init 不 load 旧图、直接 commit，是唯一一条不经 load 的写路径，单独钉住。"""
        新 = self.假出厂.parent / "萝卜" / graph.PRESET_FILENAME
        新.parent.mkdir()
        code, out = cli("--graph", 新, "--kind", "preset", "init", "--empty")
        self.assertEqual(code, 1, "在包内起一份新预设图也该拒：%s" % out)
        self.assertFalse(新.exists(), "拒了却落了盘：%s" % 新)

    def test_另存到包内也被拒(self):
        """另存是新开的写路径（ADR-0023），它同样不许把东西落进包里。"""
        ws = 工.起工作区(self.tmp / "案件", 预设图=self.个人)
        目标 = self.假出厂.parent / "另存来的"
        r = ws.调("export-preset", "--out", str(目标))
        self.assertEqual(r.code, 1, r)
        self.assertIn("ADR-0020", r.err)
        self.assertFalse(目标.exists(), "拒了却建了目录：%s" % 目标)

    def test_拒绝消息告诉人往哪走(self):
        out = self.拒("add-module", "--title", "新模块", "--id", "m-xin")
        for 片 in ("export-preset", "个人预设图", "PR"):
            self.assertIn(片, out, "拒绝消息里没有「%s」，看不出下一步该做什么：%s" % (片, out))

    def test_同一条命令写个人预设图就过(self):
        """拒的是位置，不是操作：同样的 add-node 落在包外的个人预设图上照常写得进。"""
        code, out = cli("--graph", self.个人图, "--kind", "preset",
                        "add-node", "--module", "养护", "--title", "补种记录", "--id", "n-buzhong")
        self.assertEqual(code, 0, out)
        data = json.loads(self.个人图.read_text(encoding="utf-8"))
        标题 = [n["标题"] for m in data["模块"] for n in m["节点"]]
        self.assertIn("补种记录", 标题)


class 只拦写不拦读Case(Base):
    """出厂件的只读用法一条都不能碎：起手拿它整份拷入就是最要紧的那一条。"""

    def test_validate读出厂件照旧(self):
        code, out = cli("--graph", self.出厂图, "--kind", "preset", "validate")
        self.assertEqual(code, 0, "validate 是只读的，不该被这条拒拦住：%s" % out)

    def test_起手拿出厂件整份拷入照旧(self):
        ws = 工.起工作区(self.tmp / "案件", 预设图=self.假出厂)
        self.assertEqual(ws.模块标题(), ["整地", "播种", "养护", "收获"])
        self.assertEqual(self.字节(self.出厂图), self.字节(self.个人图), "起手只读它，一字不动")

    def test_案件图落在包内不受这条拦(self):
        """这条规则只管预设图。案件图落进仓库是另一条硬边界的病，且该在起手那一刻拦，
        不该在第 37 条条目落盘时才报。"""
        code, out = cli("--graph", self.假出厂 / "图.json", "init", "--preset", self.个人)
        self.assertEqual(code, 0, "案件图不归这条规则管：%s" % out)


class 判据Case(Base):
    """两条判据各自成立，且真包确实在射程里。"""

    def test_判据一算出来的就是仓库里那个目录(self):
        """真包这一侧唯一的断言，只读、不碰文件：哪天 graph.py 挪了位置、或出厂预设图改了
        目录名，这里红。它与上面那些拿假包跑的「拒」合起来，才等于「包内预设图字节不变」。"""
        算出的 = (SCRIPT.resolve().parent / graph.PRESET_ROOT_RELATIVE).resolve()
        self.assertEqual(算出的, 真包.resolve(),
                         "graph.py 按自己的位置算出的 assets/预设图/ 与仓库里那个对不上")
        self.assertTrue(graph.in_package(真包 / "破产" / graph.PRESET_FILENAME),
                        "仓库里出厂预设图该在的位置没被判成包内：判据 ① 断了")

    def test_判据二认别处拷来的一份包(self):
        self.assertTrue(graph.in_package(self.出厂图), "形如 assets/预设图/<名> 的没被认出")

    def test_个人预设图不被误判(self):
        self.assertFalse(graph.in_package(self.个人图), "包外的个人预设图被误判成出厂件了")

    def test_名字像但形状不对的不误判(self):
        """只有 预设图/ 的上一级恰是 assets 才算：别处叫「预设图」的目录不是出厂件。"""
        别的 = self.tmp / "我的文档" / "预设图" / "菜园"
        别的.mkdir(parents=True)
        self.assertFalse(graph.in_package(别的 / graph.PRESET_FILENAME),
                         "不在 assets/ 下的「预设图」目录不是出厂件")


if __name__ == "__main__":
    unittest.main()
