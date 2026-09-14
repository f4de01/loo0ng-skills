"""起手两场景的种子（#31 验收）：用跑器自己的种子接口回放，再看工作区状态与 状态.md 说的一致。

运行：python -m unittest tests/setup-case/test_seeds.py

回放走的是 scripts/skill-eval.py 的 replay_seed，跟 eval 跑器同一条路：种子目录里除 回放.py 与
状态.md 之外的条目原样拷进工作区，再在工作区里跑 回放.py。测试工作区跑完即弃（ADR-0015）。
"""
import importlib.util
import json
import pathlib
import shutil
import stat
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
EVALS = REPO / "evals" / "用例"
RUNNER = REPO / "scripts" / "skill-eval.py"

spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

CELLS = ["收件箱", "材料/律师陈述", "指南", "模板/官方", "模板/生成", "文书"]
已确认 = "管理人承诺书及团队人员"
已生成 = "管理人印章备案报告"


def force_rmtree(path):
    def on_error(func, target, exc_info):
        pathlib.Path(target).chmod(stat.S_IWRITE)  # 律师陈述落盘后只读
        func(target)

    shutil.rmtree(path, onerror=on_error)


class SeedCase(unittest.TestCase):
    def replay(self, seed):
        ws = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        self.addCleanup(force_rmtree, ws)
        runner.replay_seed(EVALS, seed, ws)
        return ws

    def graph(self, ws):
        return json.loads((ws / "图.json").read_text(encoding="utf-8"))

    def node(self, ws, title):
        for m in self.graph(ws)["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)


class 空目录(SeedCase):
    def test_回放后还不是案件工作区(self):
        ws = self.replay("空目录")
        self.assertFalse((ws / "图.json").exists(), "空目录种子不该有图：起手的前置就是没有图")
        self.assertFalse((ws / "AGENTS.md").exists(), "空目录种子不该有工作区指针块")
        # 收件箱/ 是律师自己拷文件进来的那个目录，起手前就可以有；六格里的其余五格由起手建。
        for cell in [c for c in CELLS if c != "收件箱"]:
            self.assertFalse((ws / cell).exists(), "空目录种子不该有六格里的 %s" % cell)

    def test_收件箱里六件各对着一个去向(self):
        ws = self.replay("空目录")
        names = sorted(p.name for p in (ws / "收件箱").iterdir())
        self.assertEqual(names, sorted([
            "债务人移交物品清单.txt", "甲法院破产案件管理人工作提示.md", "（格式）债权申报登记表.md",
            "本所自用-接管物品交接单空表.md", "未命名.txt", "管理人承诺书（已交法院）.md"]))

    def test_既有成品对得上领域图里的一个节点(self):
        ws = self.replay("空目录")
        domain = json.loads((REPO / "skills" / "engineering" / "domain" / "assets" / "破产" / "领域图.json")
                            .read_text(encoding="utf-8"))
        titles = {n["标题"]: n["id"] for m in domain["模块"] for n in m["节点"]}
        self.assertEqual(titles.get("管理人承诺书及团队人员"), "n-chengnuoshu",
                         "既有成品要登记到的那个节点在领域图里改名或换 id 了，种子说明与用例断言要跟着改")
        self.assertNotIn("联络人备案表", titles, "指南里那个「新」节点已经进领域图了，种子要换一个")


class 在办中(SeedCase):
    def setUp(self):
        self.ws = self.replay("在办中")

    def test_六格与指针块齐全(self):
        for cell in CELLS:
            self.assertTrue((self.ws / cell).is_dir(), "缺格 %s" % cell)
        self.assertIn("- 领域：破产", (self.ws / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual((self.ws / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")

    def test_整份领域图起手(self):
        domain = json.loads((REPO / "skills" / "engineering" / "domain" / "assets" / "破产" / "领域图.json")
                            .read_text(encoding="utf-8"))
        data = self.graph(self.ws)
        self.assertEqual(len(data["模块"]), len(domain["模块"]))
        self.assertEqual(sum(len(m["节点"]) for m in data["模块"]),
                         sum(len(m["节点"]) for m in domain["模块"]))
        self.assertEqual(data["领域"], "破产")

    def test_图上挂到的官方模板已拷进工作区(self):
        wanted = {n["空白模板"]["文件"] for m in self.graph(self.ws)["模块"] for n in m["节点"]
                  if isinstance(n["空白模板"], dict)}
        got = {p.name for p in (self.ws / "模板" / "官方").iterdir()}
        self.assertEqual(got, wanted, "起手图挂到的官方模板原件该都在 模板/官方/ 里")

    def test_一个已确认一个已生成未确认其余未生成(self):
        self.assertEqual([e["动作"] for e in self.node(self.ws, 已确认)["条目"]], ["生成", "确认"])
        self.assertEqual([e["动作"] for e in self.node(self.ws, 已生成)["条目"]], ["生成"])
        others = [n["标题"] for m in self.graph(self.ws)["模块"] for n in m["节点"]
                  if n["条目"] and n["标题"] not in (已确认, 已生成)]
        self.assertEqual(others, [], "只有这两个节点该有条目")

    def test_文书与审查报告都在盘上(self):
        for title in (已确认, 已生成):
            for rel in ("文书/%s/%s-v1.md" % (title, title),
                        "文书/%s/%s-v1-审查报告.md" % (title, title)):
                self.assertTrue((self.ws / rel).is_file(), "缺 %s" % rel)
        entry = self.node(self.ws, 已确认)["条目"][0]
        self.assertTrue((self.ws / entry["文书"]).is_file())
        self.assertTrue((self.ws / entry["审查报告"]).is_file())

    def test_两条律师陈述(self):
        files = sorted((self.ws / "材料" / "律师陈述").iterdir())
        self.assertEqual(len(files), 2, [p.name for p in files])
        natures = sorted(next(line.partition(": ")[2].strip() for line in
                              p.read_text(encoding="utf-8").splitlines() if line.startswith("性质:"))
                         for p in files)
        self.assertEqual(natures, ["直接陈述", "裁定"])

    def test_视图的来源与前方按领域图算出(self):
        view = json.loads((self.ws / "图视图.json").read_text(encoding="utf-8"))
        self.assertEqual(view["前方"], [], "整份起手后前方应为空")
        sources = {n["来源"] for m in view["模块"] for n in m["节点"]}
        self.assertEqual(sources, {"领域图"}, "整份起手来的节点来源都该是领域图，实际 %s" % sources)


if __name__ == "__main__":
    unittest.main()
