"""两个回流种子（#34、#91 验收）：用跑器自己的种子接口回放，再看工作区状态与 状态.md 说的一致。

运行：python -m unittest tests/domain/test_seeds.py

- 种子「回流」是开发侧那条路的摊子（ADR-0012）：「在办中」那一层的状态由
  tests/setup-case/test_seeds.py 覆盖，这里只看回流这一层加了什么：两个律师自加节点的状态、
  由 sketch.py home 拷出的那份活图、案件图指纹，以及 from-case 恰好提出已确认的那一个。
- 种子「逐节点回流」是律师侧那条路的摊子（ADR-0019）：一个合成小领域「菜园」上的案件工作区加一份活图，
  两个已生成未确认的节点一个领域图里有、一个没有，缺失判定（图视图里的「来源」）该分得开。

测试工作区跑完即弃（ADR-0015）；活图家一律指进临时目录，任何一条都不碰真的 ~/.loo0ng。
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
EVALS = REPO / "evals" / "用例"
RUNNER = REPO / "scripts" / "skill-eval.py"
SKETCH = REPO / "skills" / "engineering" / "domain" / "scripts" / "sketch.py"
DOMAIN_GRAPH = REPO / "skills" / "engineering" / "domain" / "assets" / "破产" / "领域图.json"

spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

sys.path.insert(0, str(REPO / "evals" / "共用"))
import 活图断言 as 助手  # noqa: E402  节点名与「指纹」只有一份，种子回放与四条用例的断言读的是同一处

模块 = "接管与调查"
已确认 = "乙公司甲年乙月丙日厂区接管现场情况说明"
已生成 = "乙公司食堂承包合同解除请示"

自加 = 助手.自加   # 种子「逐节点回流」里领域图没有的那个
带入 = 助手.带入   # 领域图带入的那个


class 回流种子(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = pathlib.Path(tempfile.mkdtemp(prefix="live-home-"))
        cls.was = os.environ.get("LOO0NG_HOME")
        os.environ["LOO0NG_HOME"] = str(cls.home)      # 绝不碰真的 ~/.loo0ng（ADR-0015 只生不存）
        cls.ws = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        runner.replay_seed(EVALS, "回流", cls.ws)

    @classmethod
    def tearDownClass(cls):
        if cls.was is None:
            os.environ.pop("LOO0NG_HOME", None)
        else:
            os.environ["LOO0NG_HOME"] = cls.was
        runner.remove_workspace(cls.ws)  # 只读的律师陈述与被占用的文件都归它处理
        runner.remove_workspace(cls.home)

    def 基线(self):
        return json.loads((self.ws / 助手.基线名).read_text(encoding="utf-8"))

    def 活图(self):
        return pathlib.Path(self.基线()["活图"])

    def graph(self):
        return json.loads((self.ws / "案件" / "图.json").read_text(encoding="utf-8"))

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return m, n
        raise AssertionError("案件图里找不到节点「%s」" % title)

    def test_工作区根只有案件与基线(self):
        self.assertEqual([助手.基线名, "案件"], sorted(p.name for p in self.ws.iterdir()),
                         "开发会话看得见的两样：案件工作区与回流前的基线；活图在工作区之外（ADR-0020）")

    def test_活图落在临时的活图家里而不是用户主目录(self):
        self.assertTrue(str(self.活图()).startswith(str(self.home)),
                        "活图该落在 LOO0NG_HOME 指的临时家里，实际 %s" % self.活图())
        self.assertEqual("破产", self.活图().name)

    def test_两个律师自加节点挂在领域图已有的模块下(self):
        for title in (已确认, 已生成):
            module, _ = self.node(title)
            self.assertEqual(模块, module["标题"], "「%s」该挂在「%s」下" % (title, 模块))

    def test_一个已确认一个只生成(self):
        self.assertEqual(["生成", "确认"], [e["动作"] for e in self.node(已确认)[1]["条目"]])
        self.assertEqual(["生成"], [e["动作"] for e in self.node(已生成)[1]["条目"]],
                         "只生成没拍板，判据 (a) 不满足（ADR-0012）")

    def test_标题带着本案的当事人与日期(self):
        for title in (已确认, 已生成):
            self.assertIn("乙公司", title, "标题要带案件事实，去案件化才有得改")
        self.assertIn("甲年乙月丙日", 已确认)

    def test_活图是包内出厂种子的一份拷贝(self):
        self.assertEqual(DOMAIN_GRAPH.read_bytes(), (self.活图() / "领域图.json").read_bytes(),
                         "活图该是 skills/engineering/domain/assets/破产/ 那份出厂种子的逐字副本")

    def test_基线记下了回流前的样子(self):
        基线 = self.基线()
        self.assertEqual(基线["案件图sha256"],
                         hashlib.sha256((self.ws / "案件" / "图.json").read_bytes()).hexdigest())
        self.assertEqual(助手.指纹(self.活图()), 基线["指纹"], "断言按这份指纹复核包内种子没被写")
        domain = json.loads((self.活图() / "领域图.json").read_text(encoding="utf-8"))
        self.assertEqual(基线["模块数"], len(domain["模块"]))
        self.assertEqual(基线["节点数"], sum(len(m["节点"]) for m in domain["模块"]),
                         "断言按这个数判「只多出一个节点」，不硬写 72（下一次入库会改它）")

    def test_from_case恰好提出已确认的那一个(self):
        r = subprocess.run([sys.executable, str(SKETCH), "from-case",
                            "--case", str(self.ws / "案件" / "图.json"),
                            "--domain", str(self.活图())],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(0, r.returncode, r.stderr)
        proposal = json.loads(r.stdout[r.stdout.index("{"):])
        self.assertEqual([模块], [m["标题"] for m in proposal["模块"]], "模块按领域图的标题指认")
        nodes = proposal["模块"][0]["节点"]
        self.assertEqual([已确认], [n["标题"] for n in nodes], "只生成没拍板的那个不是候选")
        self.assertEqual(self.node(已确认)[1]["id"], nodes[0]["id"], "保留案件里的原 id（ADR-0012）")



class 逐节点回流种子(unittest.TestCase):
    """律师侧那条路的摊子（#91 验收，ADR-0019）：活图、两个待确认节点、回流前的基线。"""

    @classmethod
    def setUpClass(cls):
        cls.home = pathlib.Path(tempfile.mkdtemp(prefix="live-home-"))
        cls.was = os.environ.get("LOO0NG_HOME")
        os.environ["LOO0NG_HOME"] = str(cls.home)      # 绝不碰真的 ~/.loo0ng（ADR-0015 只生不存）
        cls.ws = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        runner.replay_seed(EVALS, "逐节点回流", cls.ws)

    @classmethod
    def tearDownClass(cls):
        if cls.was is None:
            os.environ.pop("LOO0NG_HOME", None)
        else:
            os.environ["LOO0NG_HOME"] = cls.was
        runner.remove_workspace(cls.ws)
        runner.remove_workspace(cls.home)

    def 基线(self):
        return json.loads((self.ws / ".活图基线.json").read_text(encoding="utf-8"))

    def 活图(self):
        return pathlib.Path(self.基线()["活图"])

    def 案件图(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def 节点(self, title):
        for m in self.案件图()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return m, n
        raise AssertionError("案件图里找不到节点「%s」" % title)

    def test_活图落在临时的活图家里而不是用户主目录(self):
        self.assertTrue(str(self.活图()).startswith(str(self.home)),
                        "活图该落在 LOO0NG_HOME 指的临时家里，实际 %s" % self.活图())
        self.assertEqual("菜园", self.活图().name)

    def test_活图是合成小领域的一份拷贝(self):
        种子 = REPO / "evals" / "领域" / "菜园" / "领域图.json"
        self.assertEqual(种子.read_bytes(), (self.活图() / "领域图.json").read_bytes(),
                         "活图该是 evals/领域/菜园/ 那份出厂种子的逐字副本")

    def test_工作区指针块指着活图(self):
        agents = (self.ws / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("- 领域：菜园", agents)
        self.assertIn("- 领域目录：%s" % self.活图().as_posix(), agents,
                      "指针块该记活图的绝对路径（ADR-0019）：%s" % agents)

    def test_两个节点都已生成未确认(self):
        for title in (自加, 带入):
            self.assertEqual(["生成"], [e["动作"] for e in self.节点(title)[1]["条目"]],
                             "「%s」该是已生成未确认，确认那一句留给用例去打" % title)

    def test_缺失判定分得开这两个(self):
        """回流问不问，靠的是按 id 的反向减法（图视图里的「来源」），不是比标题。"""
        domain = json.loads((self.活图() / "领域图.json").read_text(encoding="utf-8"))
        领域ids = {m["id"] for m in domain["模块"]} | {n["id"] for m in domain["模块"] for n in m["节点"]}
        self.assertNotIn(self.节点(自加)[1]["id"], 领域ids, "律师自加的那个该是领域图里没有的")
        self.assertIn(self.节点(带入)[1]["id"], 领域ids, "带入的那个该是领域图里已经有的")
        view = json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))
        来源 = {n["标题"]: n["来源"] for m in view["模块"] for n in m["节点"]}
        self.assertEqual("案件", 来源[自加])
        self.assertEqual("领域图", 来源[带入])

    def test_自加的标题带着本案的当事人与日期(self):
        self.assertIn("乙家", 自加, "标题要带案件事实，去案件化才有得改")
        self.assertIn("甲年乙月丙日", 自加)
        self.assertEqual("养护", self.节点(自加)[0]["标题"], "默认模块就是它在案件图里所在的那个")

    def test_基线记下了回流前活图的样子(self):
        基线 = self.基线()
        self.assertEqual(助手.指纹(self.活图()), 基线["指纹"], "断言按这份指纹判「逐字不变」")
        domain = json.loads((self.活图() / "领域图.json").read_text(encoding="utf-8"))
        self.assertEqual(基线["模块数"], len(domain["模块"]))
        self.assertEqual(基线["节点数"], sum(len(m["节点"]) for m in domain["模块"]),
                         "断言按这个数判「只多出一个节点」，不硬写 9")

    def test_带入的那个沿用领域图的id(self):
        self.assertEqual(助手.带入的id, self.节点(带入)[1]["id"],
                         "四条用例的断言按这个 id 认「领域图里已经有」")


if __name__ == "__main__":
    unittest.main()
