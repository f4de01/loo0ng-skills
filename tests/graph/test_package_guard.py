"""包内出厂种子谁都不许写（#99 验收，ADR-0020）：引擎那条无条件拒。

运行：python -m unittest tests/graph/test_package_guard.py

挡的是 ADR-0019 开出来的那条路：律师侧逐节点回流经引擎写领域图，而 0.1.0 起手的工作区
指针块那一行指着包内的出厂种子，照写就把律师累计的东西写进了下一次 skill 包升级会整个
换掉的那份文件里，静默丢失，而律师这一侧没有 git 看得见。开发者定制领域图走同一条路
（办一遍、回流进自己的活图，再入库），所以这条拒**没有放行口**，引擎里也就没有例外分支。

两条判据取或，与 skill "setup-case" 的 setup.py 那份同源（那边只报不拒）：
  ①（真包）按 graph.py 自己的位置算出的兄弟 skill assets/，装在哪儿都成立
  ②（假包）目录名摆成 <...>/domain/assets/<领域名>，别处拷来的一份包

**拒的行为一律拿 ② 造的临时假包测**：拿真包测就是拿开发者的工作树赌一次规则，规则坏了
它会被写脏。真包这一侧只留一条只读断言，钉住「它确实落在判据 ① 的射程里」，两条合起来
才等于票里那句「包内 assets/<领域>/领域图.json 字节不变」。
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "engineering" / "graph" / "scripts" / "graph.py"
DOMAIN = REPO / "evals" / "领域" / "菜园" / "领域图.json"
真包 = REPO / "skills" / "engineering" / "domain" / "assets"

spec = importlib.util.spec_from_file_location("loo0ng_graph", SCRIPT)
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


def cli(*argv):
    r = subprocess.run([sys.executable, str(SCRIPT)] + [str(a) for a in argv],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="pkgguard-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # 判据 ②：一份摆成 <...>/domain/assets/<领域名> 的假包
        self.假种子 = self.tmp / "domain" / "assets" / "菜园"
        self.假种子.mkdir(parents=True)
        shutil.copy2(DOMAIN, self.假种子 / "领域图.json")
        self.种子图 = self.假种子 / "领域图.json"
        # 包外的活图，同样内容：每条「拒」都配一条「活图上照做」，证明拒的是位置不是操作
        self.活图目录 = self.tmp / "领域" / "菜园"
        self.活图目录.mkdir(parents=True)
        shutil.copy2(DOMAIN, self.活图目录 / "领域图.json")
        self.活图 = self.活图目录 / "领域图.json"

    def 字节(self, p):
        return pathlib.Path(p).read_bytes()


class 写包内即拒Case(Base):
    """种子上的每一种写都拒，且文件一个字节不动。"""

    def 拒(self, *argv):
        before = self.字节(self.种子图)
        code, out = cli("--graph", self.种子图, "--kind", "domain", *argv)
        self.assertEqual(code, 1, "写包内种子该拒，实际过了：%s" % out)
        self.assertIn("ADR-0020", out, "拒绝消息该点到裁定的出处：%s" % out)
        self.assertEqual(self.字节(self.种子图), before, "拒了却动了文件：引擎拒写时文件一字不动")
        return out

    def test_add_node被拒(self):
        """律师侧逐节点回流落在种子上的那一刻，就是本票存在的理由。"""
        self.拒("add-node", "--module", "养护", "--title", "补种记录", "--id", "n-buzhong",
               "--template", "无")

    def test_add_module被拒(self):
        self.拒("add-module", "--title", "新模块", "--id", "m-xin")

    def test_rename_node被拒(self):
        self.拒("rename-node", "--node", "除草", "--title", "除草与松土")

    def test_move_node被拒(self):
        self.拒("move-node", "--node", "除草", "--first")

    def test_set_time_limit被拒(self):
        self.拒("set-time-limit", "--node", "除草", "--time-limit", "七日内")

    def test_init起手也被拒(self):
        """init 不 load 旧图、直接 commit，是唯一一条不经 load 的写路径，单独钉住。"""
        新 = self.假种子.parent / "萝卜" / "领域图.json"
        新.parent.mkdir()
        code, out = cli("--graph", 新, "--kind", "domain", "init", "--empty", "--name", "萝卜")
        self.assertEqual(code, 1, "在包内起一份新领域图也该拒：%s" % out)
        self.assertFalse(新.exists(), "拒了却落了盘：%s" % 新)

    def test_拒绝消息告诉律师往哪走(self):
        """被拒的律师要一眼看见出路：活图在哪、路径怎么取、这个工作区那一行怎么换。"""
        out = self.拒("add-module", "--title", "新模块", "--id", "m-xin")
        for 片 in ("活图", "sketch.py home", "AGENTS.md", "setup-case"):
            self.assertIn(片, out, "拒绝消息里没有「%s」，律师看不出下一步该做什么：%s" % (片, out))

    def test_同一条命令写活图就过(self):
        """拒的是位置，不是操作：同样的 add-node 落在包外的活图上照常写得进。"""
        code, out = cli("--graph", self.活图, "--kind", "domain",
                        "add-node", "--module", "养护", "--title", "补种记录",
                        "--id", "n-buzhong", "--template", "无")
        self.assertEqual(code, 0, out)
        data = json.loads(self.活图.read_text(encoding="utf-8"))
        标题 = [n["标题"] for m in data["模块"] for n in m["节点"]]
        self.assertIn("补种记录", 标题)


class 只拦写不拦读Case(Base):
    """种子的只读用法一条都不能碎：eval 的回放助手与起手都拿它当领域图来源。"""

    def test_validate读种子照旧(self):
        code, out = cli("--graph", self.种子图, "--kind", "domain", "validate")
        self.assertEqual(code, 0, "validate 是只读的，不该被这条拒拦住：%s" % out)

    def test_案件图拿种子当领域图来源照旧(self):
        """--domain 指着包内种子起手案件图：evals/共用/回放助手.py 就是这么跑的，护住它。"""
        ws = self.tmp / "案件"
        ws.mkdir()
        code, out = cli("--graph", ws / "图.json", "--domain", self.假种子,
                        "init", "--full")
        self.assertEqual(code, 0, "读种子当领域图来源该照旧：%s" % out)
        self.assertTrue((ws / "图.json").is_file())

    def test_案件图落在包内不受这条拦(self):
        """这条规则只管 --kind domain（ADR-0020）。案件图落进仓库是另一条硬边界的病，
        且该在起手那一刻拦，不该在第 37 条条目落盘时才报。"""
        code, out = cli("--graph", self.假种子 / "图.json", "--domain", DOMAIN, "init", "--full")
        self.assertEqual(code, 0, "案件图不归这条规则管：%s" % out)


class 判据Case(Base):
    """两条判据各自成立，且真包确实在射程里。"""

    def test_判据一真包在射程里(self):
        """真包这一侧唯一的断言，只读：哪天 graph.py 挪了位置、或 assets/ 改了名，这里红。

        它与上面那些拿假包跑的「拒」合起来，才等于票里那句「包内 assets/<领域>/领域图.json
        字节不变」。真包一个字节都不必被这套测试碰到。"""
        真 = 真包 / "破产" / "领域图.json"
        self.assertTrue(真.is_file(), "出厂种子不在了：%s" % 真)
        self.assertTrue(graph.in_package(真), "真的出厂种子没被判成包内：判据 ① 断了")
        算出的 = (SCRIPT.resolve().parent / graph.SEED_ROOT_RELATIVE).resolve()
        self.assertEqual(算出的, 真包.resolve(),
                         "graph.py 按自己的位置算出的 assets/ 与仓库里那个对不上")

    def test_判据二认别处拷来的一份包(self):
        self.assertTrue(graph.in_package(self.种子图), "形如 domain/assets/<领域名> 的没被认出")

    def test_活图不被误判(self):
        self.assertFalse(graph.in_package(self.活图), "包外的活图被误判成种子了")

    def test_名字像但形状不对的不误判(self):
        """只有 assets/ 的上一级恰是 domain 才算：别的 skill 的 assets/ 不是种子。"""
        别的 = self.tmp / "to-docx" / "assets" / "菜园"
        别的.mkdir(parents=True)
        self.assertFalse(graph.in_package(别的 / "领域图.json"),
                         "别的 skill 的 assets/ 不是领域图的出厂种子")


if __name__ == "__main__":
    unittest.main()
