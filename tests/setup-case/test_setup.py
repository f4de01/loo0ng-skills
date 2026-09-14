"""skills/in-progress/setup-case/scripts/setup.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/setup-case/test_setup.py

缝是起手 CLI 加临时工作区里的文件：每个测试在临时目录里调 main(argv)，再看六格、图、视图、
工作区指针块与既有成品的登记条目落成了什么样。领域用合成小领域「菜园」（ADR-0015）。
文件名与内容全是合成的，没有案件内容。
"""
import contextlib
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
SCRIPT = REPO / "skills" / "in-progress" / "setup-case" / "scripts" / "setup.py"
SKETCH = REPO / "skills" / "in-progress" / "domain" / "scripts" / "sketch.py"
SEED_ASSETS = REPO / "skills" / "in-progress" / "domain" / "assets"
DOMAIN = REPO / "evals" / "领域" / "菜园"
LIVE_HOME_ENV = "LOO0NG_HOME"   # 活图的「家」，与 sketch.py、eval 跑器同一个名字

spec = importlib.util.spec_from_file_location("loo0ng_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

CELLS = ["收件箱", "材料", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书"]


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp(prefix="setup-test-"))
        self.addCleanup(shutil.rmtree, self.ws, True)

    def cli(self, *argv, workspace=None):
        args = list(argv) + ["--workspace", str(workspace or self.ws)]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = setup.main(args)
            except SystemExit as e:  # argparse 的用法错
                code = e.code if isinstance(e.code, int) else 2
        return Run(code, out.getvalue(), err.getvalue())

    def graph(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def titles(self):
        return {m["标题"]: [n["标题"] for n in m["节点"]] for m in self.graph()["模块"]}


class InitCase(Base):
    def test_空图起手落下六格与图与两份视图(self):
        r = self.cli("init", "--empty", "--name", "菜园")
        self.assertEqual(r.code, 0, r)
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assertEqual(self.graph()["领域"], "菜园")
        self.assertEqual(self.graph()["模块"], [])
        for name in ("图视图.md", "图视图.json"):
            self.assertTrue((self.ws / name).is_file(), "缺视图 %s" % name)

    def test_整份领域图起手带进全部模块与节点(self):
        r = self.cli("init", "--full", "--domain", str(DOMAIN))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(len(self.graph()["模块"]), 4)
        self.assertEqual(sum(len(m["节点"]) for m in self.graph()["模块"]), 9)
        self.assertEqual(json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))["前方"], [])

    def assert_指针块(self, 领域, 领域目录文本):
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- 领域：%s" % 领域, agents)
        self.assertIn("- 领域目录：%s" % 领域目录文本, agents)
        for expected in ("图.json", "图视图.md", "图视图.json", "doit", "只读"):
            self.assertIn(expected, agents, "指针块里缺 %s" % expected)
        self.assertEqual((self.ws / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_定制图起手(self):
        custom = self.ws.parent / ("定制图-%s.json" % self.ws.name)
        self.addCleanup(custom.unlink, True)
        custom.write_text(json.dumps({"格式版本": 1, "领域": "菜园", "模块": [
            {"id": "m-x", "标题": "只有一个模块", "节点": [
                {"id": "n-x", "标题": "只有一个节点", "空白模板": "无", "条目": []}]}]},
            ensure_ascii=False), encoding="utf-8")
        r = self.cli("init", "--from", str(custom), "--domain", str(DOMAIN))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.titles(), {"只有一个模块": ["只有一个节点"]})
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_指针块四项齐全(self):
        self.cli("init", "--full", "--domain", str(DOMAIN))
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_领域目录给的是领域图文件也记成目录(self):
        self.cli("init", "--full", "--domain", str(DOMAIN / "领域图.json"))
        self.assertIn("- 领域目录：%s" % DOMAIN.as_posix(),
                      (self.ws / "AGENTS.md").read_text(encoding="utf-8"))

    def test_没有领域目录时指针块照样落下(self):
        self.cli("init", "--empty", "--name", "菜园")
        self.assert_指针块("菜园", "（无")
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("空图", agents,
                         "没给领域目录跟起手图选了哪一种是两回事：--from 的定制图也可以没有领域目录")

    def test_空图起手也验六格与指针块(self):
        self.cli("init", "--empty", "--domain", str(DOMAIN))
        for rel in CELLS:
            self.assertTrue((self.ws / rel).is_dir(), "缺格 %s" % rel)
        self.assert_指针块("菜园", DOMAIN.as_posix())

    def test_已有图就拒绝且一字不动(self):
        (self.ws / "图.json").write_text("原样", encoding="utf-8")
        r = self.cli("init", "--empty", "--name", "菜园")
        self.assertEqual(r.code, 1, r)
        self.assertIn("图.json", r.err)
        self.assertEqual((self.ws / "图.json").read_text(encoding="utf-8"), "原样")
        self.assertFalse((self.ws / "收件箱").exists(), "拒绝时不该建六格")
        self.assertFalse((self.ws / "AGENTS.md").exists(), "拒绝时不该写指针块")

    def test_三选一必须恰好一个(self):
        r = self.cli("init", "--empty", "--full", "--domain", str(DOMAIN))
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists())
        self.assertFalse((self.ws / "AGENTS.md").exists())
        r = self.cli("init")
        self.assertEqual(r.code, 1, r)

    def test_引擎拒写时不留半个工作区(self):
        r = self.cli("init", "--empty")  # 既没有 --domain 也没有 --name，引擎拒
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists())
        self.assertFalse((self.ws / "AGENTS.md").exists())
        self.assertFalse((self.ws / "收件箱").exists())


class TemplateCase(Base):
    def make_domain(self, files):
        root = pathlib.Path(tempfile.mkdtemp(prefix="setup-domain-"))
        self.addCleanup(shutil.rmtree, root, True)
        shutil.copy2(DOMAIN / "领域图.json", root / "领域图.json")
        if files is not None:
            (root / "模板").mkdir()
            for name in files:
                (root / "模板" / name).write_bytes(b"synthetic")
        return root

    def test_起手图挂到的官方模板拷进模板官方(self):
        root = self.make_domain(["施肥记录.docx", "播种登记.docx", "采摘记录.docx", "没人挂的.docx"])
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        got = sorted(p.name for p in (self.ws / "模板" / "官方").iterdir())
        self.assertEqual(got, sorted(["施肥记录.docx", "播种登记.docx", "采摘记录.docx"]),
                         "只拷起手图上挂到的那几件")

    def test_空图起手不拷模板(self):
        root = self.make_domain(["施肥记录.docx"])
        self.cli("init", "--empty", "--domain", str(root))
        self.assertEqual(list((self.ws / "模板" / "官方").iterdir()), [])

    def test_领域目录里缺模板原件只报不拒(self):
        root = self.make_domain(["施肥记录.docx"])
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        self.assertIn("播种登记.docx", r.out)
        self.assertEqual(sorted(p.name for p in (self.ws / "模板" / "官方").iterdir()), ["施肥记录.docx"])

    def test_领域目录没有模板格也不拒(self):
        root = self.make_domain(None)
        r = self.cli("init", "--full", "--domain", str(root))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(list((self.ws / "模板" / "官方").iterdir()), [])


class 活图Case(Base):
    """起手落进指针块的领域目录是活图，不是 skill 包内的出厂种子（#90，ADR-0019）。

    这是两件 skill 接在一起的那一处：路径由 skill "domain" 的 sketch.py home 取，
    起手把它原样记进工作区 AGENTS.md，之后每一件 skill 都从那一行读。
    """

    def setUp(self):
        super().setUp()
        self.roots = pathlib.Path(tempfile.mkdtemp(prefix="setup-live-"))
        self.addCleanup(shutil.rmtree, self.roots, True)
        self.seed_root = self.roots / "assets"      # 装成 skill 包内的出厂种子根
        (self.seed_root / "菜园").mkdir(parents=True)
        shutil.copy2(DOMAIN / "领域图.json", self.seed_root / "菜园" / "领域图.json")
        self.live_root = self.roots / "领域"

    def home(self, name="菜园"):
        r = subprocess.run([sys.executable, str(SKETCH), "home", "--name", name,
                            "--live-root", str(self.live_root), "--seed-root", str(self.seed_root)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        return pathlib.Path(r.stdout.splitlines()[0].split("：", 1)[1])

    def test_指针块记的是活图不是种子(self):
        live = self.home()
        r = self.cli("init", "--full", "--domain", str(live))
        self.assertEqual(r.code, 0, r)
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- 领域目录：%s" % live.as_posix(), agents)
        self.assertNotIn((self.seed_root / "菜园").as_posix(), agents,
                         "指针块里不该出现出厂种子的路径：律师累计的东西不在那里")
        self.assertNotIn("assets", agents, "指针块里的领域目录不该指进 skill 包的 assets/")

    def test_起手用的是活图上的内容(self):
        """活图与种子分家之后，起手读的是活图：改了活图，起手图就跟着变。"""
        live = self.home()
        (live / "领域图.json").write_text(json.dumps(
            {"格式版本": 1, "领域": "菜园", "模块": [
                {"id": "m-live-only", "标题": "只有活图有的模块", "节点": []}]}, ensure_ascii=False),
            encoding="utf-8")
        r = self.cli("init", "--full", "--domain", str(live))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(list(self.titles()), ["只有活图有的模块"])

    def test_给了包内种子路径就说一句(self):
        """只报不拒：起手是读，开发侧的种子回放本来就直接对着种子起手；写那一刻由引擎拒（ADR-0020）。"""
        种子 = SEED_ASSETS / "破产"
        r = self.cli("init", "--empty", "--domain", str(种子))
        self.assertEqual(r.code, 0, r)
        self.assertIn("出厂种子", r.out, "给的是包内种子，起手要说一句：%r" % r)
        self.assertIn("sketch.py home", r.out, "说了就要给出取活图路径的那条命令：%r" % r)

    def test_给的是活图就不啰嗦(self):
        live = self.home()
        r = self.cli("init", "--full", "--domain", str(live))
        self.assertNotIn("出厂种子", r.out, "给的就是活图，不该报那一句：%r" % r)


class 一条命令Case(Base):
    """律师侧起手只打一条命令：init 自己子进程调 sketch.py home 取活图路径（#97，ADR-0019）。

    `--domain-name <领域名>` 给领域名，路径由 init 自己取；`--domain <路径>` 留给开发侧
    （种子回放、开发者定制图）。活图家用 LOO0NG_HOME 挪进临时目录（ADR-0015 只生不存），
    永远不碰律师真的 ~/.loo0ng。
    """

    def setUp(self):
        super().setUp()
        self.home = pathlib.Path(tempfile.mkdtemp(prefix="setup-home-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        旧 = os.environ.get(LIVE_HOME_ENV)
        os.environ[LIVE_HOME_ENV] = str(self.home)
        self.addCleanup(self.还原活图家, 旧)

    def 还原活图家(self, 旧):
        if 旧 is None:
            os.environ.pop(LIVE_HOME_ENV, None)
        else:
            os.environ[LIVE_HOME_ENV] = 旧

    def 摆一份活图(self, name="菜园"):
        live = self.home / "领域" / name
        live.mkdir(parents=True)
        shutil.copy2(DOMAIN / "领域图.json", live / "领域图.json")
        return live

    def 摆一份假包(self, name="菜园"):
        """装成一份 skill 包：`<pkg>/domain/` 下 scripts/sketch.py 与 assets/<领域名>/ 三样。

        sketch.py 的出厂种子根按它自身的位置算（`../assets`），所以把它拷进这个假包里，
        种子就是这份合成的菜园（ADR-0015：脚本层用合成小领域，真的 assets/ 一个字节不碰）。
        回 --sketch 该指的那个路径。
        """
        pkg = pathlib.Path(tempfile.mkdtemp(prefix="setup-pkg-")) / "domain"
        self.addCleanup(shutil.rmtree, pkg.parent, True)
        (pkg / "scripts").mkdir(parents=True)
        shutil.copy2(SKETCH, pkg / "scripts" / "sketch.py")
        seed = pkg / "assets" / name
        (seed / "模板").mkdir(parents=True)
        (seed / "指引手册").mkdir(parents=True)
        shutil.copy2(DOMAIN / "领域图.json", seed / "领域图.json")
        (seed / "模板" / "施肥记录.docx").write_bytes(b"synthetic")
        (seed / "指引手册" / "合成手册.md").write_text("合成的指引手册", encoding="utf-8")
        return pkg / "scripts" / "sketch.py"

    def test_一条命令起手指针块记的就是活图(self):
        live = self.摆一份活图()
        r = self.cli("init", "--full", "--domain-name", "菜园")
        self.assertEqual(r.code, 0, r)
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- 领域目录：%s" % live.as_posix(), agents,
                      "律师只打了这一条命令，指针块记的仍该是活图")
        self.assertNotIn("assets", agents, "指针块里的领域目录不该指进 skill 包的 assets/")
        self.assertEqual(self.graph()["领域"], "菜园")
        self.assertTrue(self.titles(), "--full 该按活图上那份领域图整份起手")

    def test_首次起手一条命令就把出厂种子拷成活图(self):
        """活图位置上还没有这个领域时，那一条命令自己把三样拷出来（#90 的验收项经这条路仍绿）。"""
        r = self.cli("init", "--empty", "--domain-name", "菜园", "--sketch", str(self.摆一份假包()))
        self.assertEqual(r.code, 0, r)
        live = self.home / "领域" / "菜园"
        self.assertTrue((live / "领域图.json").is_file(), "首次起手该把出厂种子整份拷成活图")
        self.assertTrue((live / "模板").is_dir() and (live / "指引手册").is_dir(),
                        "活图该是出厂种子的整份副本：%s" % sorted(x.name for x in live.iterdir()))
        self.assertIn("- 领域目录：%s" % live.as_posix(),
                      (self.ws / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("活图", r.out, "home 的回显该照抄给律师：%r" % r)

    def test_两端认的是同一个回显前缀(self):
        """跨 skill 的契约就钉在这一个前缀上：两件 skill 互不 import，各持一份中文字面量
        （setup.py 的 LIVE_PREFIX 与 sketch.py 回显的第一行）。这一条同时钉住两端，
        哪一边先改了这个词，起手取活图就会静静地拿到错的路径。"""
        sketch = self.摆一份假包()
        r = subprocess.run([sys.executable, str(sketch), "home", "--name", "菜园"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        第一行 = r.stdout.splitlines()[0]
        self.assertTrue(第一行.startswith(setup.LIVE_PREFIX),
                        "sketch.py home 的第一行该以 %r 起头，实际 %r" % (setup.LIVE_PREFIX, 第一行))

    def test_两种传法不能同时给(self):
        r = self.cli("init", "--full", "--domain", str(DOMAIN), "--domain-name", "菜园")
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists(), "拒绝时不该落图")
        self.assertFalse((self.ws / "AGENTS.md").exists(), "拒绝时不该写指针块")
        self.assertFalse((self.ws / "收件箱").exists(), "拒绝时不该建六格")

    def test_领域名不要给两遍(self):
        """--domain-name 与 --name 给成不一样的，指针块的「领域」与「领域目录」会各指一处。"""
        self.摆一份活图()
        r = self.cli("init", "--empty", "--domain-name", "菜园", "--name", "果园")
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "图.json").exists(), "拒绝时不该落图")
        self.assertFalse((self.ws / "AGENTS.md").exists(), "拒绝时不该写指针块")

    def test_取不到活图就一格不建一个字不写(self):
        """活图与出厂种子都没有的领域，home 拒，起手跟着拒：此时还什么都没写。"""
        r = self.cli("init", "--empty", "--domain-name", "还没有这个领域")
        self.assertEqual(r.code, 1, r)
        self.assertIn("活图", r.err, "该把 home 拒的原话照抄出来：%r" % r)
        self.assertFalse((self.ws / "图.json").exists())
        self.assertFalse((self.ws / "AGENTS.md").exists())
        self.assertFalse((self.ws / "收件箱").exists())

    def test_开发侧给路径那条路不碰活图家(self):
        """--domain 给路径时 init 不去调 home：种子回放与定制图那条路一个字没动。"""
        r = self.cli("init", "--full", "--domain", str(DOMAIN))
        self.assertEqual(r.code, 0, r)
        self.assertFalse((self.home / "领域").exists(), "给了 --domain 就不该再去取活图")
        self.assertIn("- 领域目录：%s" % DOMAIN.as_posix(),
                      (self.ws / "AGENTS.md").read_text(encoding="utf-8"))

    def test_定制图也能只给领域名(self):
        live = self.摆一份活图()
        custom = self.home / "定制图.json"
        custom.write_text(json.dumps({"格式版本": 1, "领域": "菜园", "模块": [
            {"id": "m-only", "标题": "只有定制图有的模块", "节点": []}]}, ensure_ascii=False),
            encoding="utf-8")
        r = self.cli("init", "--from", str(custom), "--domain-name", "菜园")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(list(self.titles()), ["只有定制图有的模块"])
        self.assertIn("- 领域目录：%s" % live.as_posix(),
                      (self.ws / "AGENTS.md").read_text(encoding="utf-8"))


class RegisterCase(Base):
    def setUp(self):
        super().setUp()
        self.cli("init", "--full", "--domain", str(DOMAIN))
        self.doc = self.ws / "材料" / "旧的下种记录.md"
        self.doc.write_text("合成的既有成品", encoding="utf-8")

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)

    def test_既有成品登记为已生成来源律师(self):
        r = self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md",
                     "--words", "都按建议登记")
        self.assertEqual(r.code, 0, r)
        entries = self.node("下种")["条目"]
        self.assertEqual(len(entries), 1, entries)
        self.assertEqual(entries[0]["动作"], "生成")
        self.assertEqual(entries[0]["来源"], "律师")
        self.assertEqual(entries[0]["文书"], "材料/旧的下种记录.md")

    def test_登记不确认任何节点(self):
        self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md", "--words", "都按建议登记")
        actions = [e["动作"] for m in self.graph()["模块"] for n in m["节点"] for e in n["条目"]]
        self.assertEqual(actions, ["生成"], "起手登记只该落生成条目")

    def test_审查报告按固定模板落在文书目录下(self):
        self.cli("register", "--node", "下种", "--doc", "材料/旧的下种记录.md", "--words", "都按建议登记")
        review = self.ws / "文书" / "下种" / "下种-v1-审查报告.md"
        self.assertTrue(review.is_file(), "没写审查报告")
        text = review.read_text(encoding="utf-8")
        for heading in ("## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"):
            self.assertIn(heading, text, "审查报告缺固定段 %s" % heading)
        self.assertIn("都按建议登记", text)
        self.assertIn("材料/旧的下种记录.md", text)
        self.assertEqual(self.node("下种")["条目"][0]["审查报告"], "文书/下种/下种-v1-审查报告.md")

    def test_文书不存在就拒(self):
        r = self.cli("register", "--node", "下种", "--doc", "材料/不存在.md", "--words", "都按建议登记")
        self.assertEqual(r.code, 1, r)
        self.assertEqual(self.node("下种")["条目"], [])
        self.assertFalse((self.ws / "文书" / "下种").exists(), "拒绝时不该留审查报告")

    def test_越界路径就拒(self):
        for bad in ("../外面.md", "D:/外面.md", "材料\\反斜杠.md"):
            r = self.cli("register", "--node", "下种", "--doc", bad, "--words", "都按建议登记")
            self.assertEqual(r.code, 1, "%s 应被拒：%r" % (bad, r))

    def test_引擎拒写时回滚审查报告(self):
        r = self.cli("register", "--node", "图里没有的节点", "--doc", "材料/旧的下种记录.md",
                     "--words", "都按建议登记")
        self.assertEqual(r.code, 1, r)
        self.assertFalse((self.ws / "文书" / "图里没有的节点").exists(), "拒绝时不该留审查报告")

    def test_没有图就拒(self):
        empty = pathlib.Path(tempfile.mkdtemp(prefix="setup-nograph-"))
        self.addCleanup(shutil.rmtree, empty, True)
        r = self.cli("register", "--node", "下种", "--doc", "材料/x.md", "--words", "x", workspace=empty)
        self.assertEqual(r.code, 1, r)


if __name__ == "__main__":
    unittest.main()
