"""种子「兜底」（#32 验收）：用跑器自己的种子接口回放，再看工作区状态与 状态.md 说的一致。

运行：python -m unittest tests/doit/test_seeds.py

「在办中」那部分的状态由 tests/setup-case/test_seeds.py 覆盖，这里只看兜底这一层加了什么：
收件箱里那件律师自写的 docx、借来的材料、以及回放没有替律师把它登记进图。
门禁在这里不跑（要起 Word，约 7 秒）：落盘件过不过门禁由 evals/用例/兜底登记 的断言复核。
测试工作区跑完即弃（ADR-0015）。
"""
import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
EVALS = REPO / "evals" / "用例"
RUNNER = REPO / "scripts" / "skill-eval.py"

spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

成品 = "印章备案-我自己写的.docx"
节点 = "管理人印章备案报告"


class 兜底(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = pathlib.Path(tempfile.mkdtemp(prefix="seed-test-"))
        runner.replay_seed(EVALS, "兜底", cls.ws)

    @classmethod
    def tearDownClass(cls):
        runner.remove_workspace(cls.ws)  # 只读的律师陈述与被占用的文件都归它处理

    def graph(self):
        return json.loads((self.ws / "图.json").read_text(encoding="utf-8"))

    def node(self, title):
        for m in self.graph()["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)

    def test_收件箱里恰有那件律师自写的docx(self):
        left = sorted(p.name for p in (self.ws / "收件箱").rglob("*"))
        self.assertEqual([成品], left, "收件箱里该只有律师自写的那一件，稿子不留在盘上")
        with zipfile.ZipFile(str(self.ws / "收件箱" / 成品)) as z:
            body = z.read("word/document.xml").decode("utf-8")
        self.assertIn("乙公司管理人章", body, "正文该是照稿子转出来的")
        self.assertNotIn("XX", body, "模板占位不该留在成品里")

    def test_在办中那层的材料与状态还在(self):
        self.assertTrue((self.ws / "材料" / "债务人移交物品清单.txt").is_file(),
                        "本种子借「在办中」的材料，两份审查报告的生成依据指着它")
        self.assertEqual(["生成"], [e["动作"] for e in self.node(节点)["条目"]],
                         "印章备案在种子里是已生成未确认")

    def test_回放没有替律师登记(self):
        docs = self.ws / "文书" / 节点
        self.assertEqual(sorted(p.name for p in docs.iterdir()),
                         ["%s-v1-审查报告.md" % 节点, "%s-v1.md" % 节点],
                         "登记是办节点那一句话的事，种子只摆好起点")


if __name__ == "__main__":
    unittest.main()
