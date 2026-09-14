"""活图与出厂种子（#90 验收，ADR-0019）：sketch.py home 的三条规矩。

运行：python -m unittest tests/domain/test_home.py

缝是 home 这一条命令加两个临时根（活图根、种子根）：不存在就拷、已存在就一个字不动、
包升级（种子变了）之后活图逐字不变。任何一个测试都不碰真的 ~/.loo0ng：活图根一律显式给
--live-root 或经环境变量 LOO0NG_HOME 指进临时目录（ADR-0015 只生不存）。
领域用合成小领域「菜园」，没有案件内容。
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "in-progress" / "domain" / "scripts" / "sketch.py"
菜园 = REPO / "evals" / "领域" / "菜园"

spec = importlib.util.spec_from_file_location("loo0ng_sketch", SCRIPT)
sketch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sketch)


def 指纹(root: pathlib.Path) -> dict:
    """目录里每个文件的相对路径 -> 内容 sha256。逐字比就比这个。"""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="home-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.live_root = self.tmp / "活图根" / "领域"
        self.seed_root = self.tmp / "种子根"
        # 出厂种子：三样齐全的合成领域「菜园」（领域图 + 模板/ + 指引手册/）
        seed = self.seed_root / "菜园"
        (seed / "模板").mkdir(parents=True)
        (seed / "指引手册").mkdir(parents=True)
        shutil.copy2(菜园 / "领域图.json", seed / "领域图.json")
        (seed / "模板" / "施肥记录.docx").write_bytes(b"synthetic-template")
        (seed / "指引手册" / "种菜手册.docx").write_bytes(b"synthetic-handbook")
        self.seed = seed

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sketch.main(list(argv))
            except SystemExit as e:  # argparse 的用法错
                code = e.code if isinstance(e.code, int) else 2
        return Run(code, out.getvalue(), err.getvalue())

    def home(self, name="菜园", *extra):
        return self.cli("home", "--name", name, *extra,
                        "--live-root", str(self.live_root), "--seed-root", str(self.seed_root))

    @property
    def live(self):
        return self.live_root / "菜园"


class 首次起手拷种子(Base):
    def test_活图不在就整份拷一份(self):
        self.assertFalse(self.live.exists(), "前置：活图位置上还没有这个领域")
        r = self.home()
        self.assertEqual(r.code, 0, r)
        self.assertTrue(self.live.is_dir(), "活图没建出来：%r" % r)
        self.assertEqual(指纹(self.live), 指纹(self.seed), "活图该是种子的逐字副本")
        self.assertIn("首次起手", r.out)

    def test_回显第一行就是活图的绝对路径(self):
        r = self.home()
        第一行 = r.out.splitlines()[0]
        self.assertTrue(第一行.startswith("活图："), "第一行要能让模型直接取路径：%r" % 第一行)
        路径 = pathlib.Path(第一行.split("：", 1)[1])
        self.assertTrue(路径.is_absolute(), "活图路径要给绝对路径：%r" % 路径)
        self.assertEqual(路径.resolve(), self.live.resolve())

    def test_拷贝不留半份也不留临时名(self):
        self.home()
        剩下 = sorted(p.name for p in self.live_root.iterdir())
        self.assertEqual(剩下, ["菜园"], "活图根里不该留下拷贝用的临时目录：%s" % 剩下)

    def test_既没有活图也没有种子就拒(self):
        r = self.home("没有这个领域")
        self.assertEqual(r.code, 1, r)
        self.assertIn("空图起手", r.err, "拒的时候要说清新领域怎么办：%r" % r)
        self.assertIn("--empty", r.err, "拒的时候也要指出开发侧造这个领域走哪条路（#103）：%r" % r)
        self.assertFalse((self.live_root / "没有这个领域").exists(), "拒绝时不该建半个目录")

    def test_领域名不能带路径分隔符(self):
        for bad in ("../外面", "破产/模板", "a\\b", ".", ""):
            r = self.home(bad)
            self.assertEqual(r.code, 1, "%r 应被拒：%r" % (bad, r))


class 新领域从空图起手(Base):
    """home --empty（#103 验收，ADR-0020）：开发者造一份全新领域的种子，起点是这里。

    两侧同一条路的意思就是开发侧也享受「新领域从空图起手」这条低入场费；卡在「活图建不出来」
    那就不是同一条路。
    """

    def test_建目录并起一份空领域图(self):
        新 = self.live_root / "果园"
        r = self.home("果园", "--empty")
        self.assertEqual(r.code, 0, r)
        self.assertTrue(新.is_dir(), "活图目录没建出来：%r" % r)
        self.assertEqual(sorted(p.name for p in 新.iterdir()), ["领域图.json"],
                         "--empty 只起领域图，模板/ 与 指引手册/ 等它有内容了再建")
        data = json.loads((新 / "领域图.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"格式版本": 1, "领域": "果园", "模块": []})

    def test_回显第一行仍是活图的绝对路径(self):
        r = self.home("果园", "--empty")
        第一行 = r.out.splitlines()[0]
        self.assertTrue(第一行.startswith("活图："), "第一行要能让模型直接取路径：%r" % 第一行)
        self.assertEqual(pathlib.Path(第一行.split("：", 1)[1]).resolve(),
                         (self.live_root / "果园").resolve())

    def test_起出来的空领域图引擎认(self):
        """它是接下来逐节点回流要写的那一份：引擎读不动就白起了。"""
        self.home("果园", "--empty")
        engine = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"
        r = subprocess.run([sys.executable, str(engine), "--graph",
                            str(self.live_root / "果园" / "领域图.json"), "--kind", "domain", "validate"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_包里已有种子就拒且不建目录(self):
        """不给它盖一份空的：种子在，不带 --empty 跑一次就是整份拷过去。"""
        r = self.home("菜园", "--empty")
        self.assertEqual(r.code, 1, r)
        self.assertIn("出厂种子", r.err)
        self.assertFalse(self.live.exists(), "拒绝时不该建半个目录")

    def test_已有活图就一个字不动(self):
        self.home("果园", "--empty")
        (self.live_root / "果园" / "领域图.json").write_text(
            '{"格式版本": 1, "领域": "果园", "模块": [{"id": "m-1", "标题": "剪枝", "节点": []}]}',
            encoding="utf-8")
        累计 = 指纹(self.live_root / "果园")
        r = self.home("果园", "--empty")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(指纹(self.live_root / "果园"), 累计, "第二次跑把活图覆盖了")
        self.assertIn("一个字没动", r.out)

    def test_引擎拒了就不留半个活图(self):
        r = self.cli("home", "--name", "果园", "--empty", "--live-root", str(self.live_root),
                     "--seed-root", str(self.seed_root), "--engine", str(self.tmp / "没有这个引擎.py"))
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.live_root / "果园").exists(), "拒绝时不该留下半个活图")
        剩下 = sorted(p.name for p in self.live_root.iterdir()) if self.live_root.is_dir() else []
        self.assertEqual(剩下, [], "活图根里不该留下拷贝用的临时目录：%s" % 剩下)


class 已有活图就一个字不动(Base):
    def setUp(self):
        super().setUp()
        self.home()
        # 律师在活图上累计出来的东西：改过的领域图、多出来的一件模板
        (self.live / "领域图.json").write_text('{"格式版本": 1, "领域": "菜园", "模块": []}',
                                               encoding="utf-8")
        (self.live / "模板" / "律师自己加的.docx").write_bytes(b"lawyer-added")
        self.累计 = 指纹(self.live)

    def test_再起手一次不覆盖(self):
        r = self.home()
        self.assertEqual(r.code, 0, r)
        self.assertEqual(指纹(self.live), self.累计, "第二次起手把活图覆盖了")
        self.assertIn("一个字没动", r.out)

    def test_模拟一次包升级之后活图逐字不变(self):
        """本票存在的理由：律师再跑一次 npx skills add 升级，累计半年的图不许被抹掉。

        升级 = 包内出厂种子被整个换掉（领域图改了、模板改了、还多出一件）。
        """
        (self.seed / "领域图.json").write_text(
            '{"格式版本": 1, "领域": "菜园", "模块": [{"id": "m-新", "标题": "新版模块", "节点": []}]}',
            encoding="utf-8")
        (self.seed / "模板" / "施肥记录.docx").write_bytes(b"synthetic-template-v2")
        (self.seed / "模板" / "新版才有的.docx").write_bytes(b"brand-new")
        r = self.home()
        self.assertEqual(r.code, 0, r)
        self.assertEqual(指纹(self.live), self.累计, "包一升级就把活图抹了，这正是 ADR-0019 要挡的事故")
        self.assertNotIn("新版才有的.docx", [p.name for p in (self.live / "模板").iterdir()],
                         "种子新增的件也不该漏进活图：活图只由律师自己改")


class 活图根怎么算(Base):
    """默认位置是 ~/.loo0ng/领域/；环境变量 LOO0NG_HOME 换的是 .loo0ng 那一层。"""

    @contextlib.contextmanager
    def 环境(self, **kv):
        旧 = {k: os.environ.get(k) for k in kv}
        os.environ.update({k: v for k, v in kv.items() if v is not None})
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
        try:
            yield
        finally:
            for k, v in 旧.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_不设环境变量时落在用户主目录下(self):
        with self.环境(LOO0NG_HOME=None):
            root = sketch.live_root()
        期望 = (pathlib.Path.home() / ".loo0ng" / "领域").resolve()
        self.assertEqual(root, 期望, "活图默认住 ~/.loo0ng/领域/：跨案件，不挂在任何案件根下")

    def test_环境变量换家(self):
        with self.环境(LOO0NG_HOME=str(self.tmp / "另一个家")):
            root = sketch.live_root()
        self.assertEqual(root, (self.tmp / "另一个家" / "领域").resolve())

    def test_显式给的活图根压过环境变量(self):
        with self.环境(LOO0NG_HOME=str(self.tmp / "另一个家")):
            self.assertEqual(sketch.live_root(str(self.live_root)), self.live_root.resolve())

    def test_种子根默认是本skill的assets(self):
        self.assertEqual(sketch.seed_root(),
                         (REPO / "skills" / "in-progress" / "domain" / "assets").resolve())


class 真的破产种子(Base):
    """出厂的破产种子拷得动、拷完三样齐全：起手拷的是它，22 件约 540 KB，一次性成本。"""

    def test_整份拷过去三样齐全(self):
        r = self.cli("home", "--name", "破产", "--live-root", str(self.live_root))
        self.assertEqual(r.code, 0, r)
        live = self.live_root / "破产"
        self.assertEqual(指纹(live), 指纹(REPO / "skills" / "in-progress" / "domain" / "assets" / "破产"),
                         "活图该是出厂种子的逐字副本")
        self.assertEqual(sorted(p.name for p in live.iterdir()), ["指引手册", "模板", "领域图.json"])


if __name__ == "__main__":
    unittest.main()
