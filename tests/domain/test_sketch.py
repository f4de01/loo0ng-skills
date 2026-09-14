"""skills/in-progress/domain/scripts/sketch.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/domain/test_sketch.py

缝是雏形 CLI 加工作区里的文件：每个测试在临时目录里调 main(argv)，再读回显与 图.json、两份视图断言。
领域一律用合成小领域 evals/领域/菜园/，证明雏形机制不认破产语义（ADR-0015）。写入经图引擎子进程（#29）。
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "in-progress" / "domain" / "scripts" / "sketch.py"
ENGINE = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"
DOMAIN_DIR = REPO / "evals" / "领域" / "菜园"

spec = importlib.util.spec_from_file_location("loo0ng_sketch", SCRIPT)
sketch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sketch)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


def engine(*argv):
    r = subprocess.run([sys.executable, str(ENGINE), *map(str, argv)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    return r.stdout


class SketchCase(unittest.TestCase):
    """每个测试一个临时工作区：按菜园整份起手的案件图，或一张空领域图。"""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="sketch-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.graph_path = self.tmp / "图.json"
        self.proposal_path = self.tmp / "雏形.json"

    def full_case_graph(self):
        engine("--graph", self.graph_path, "--domain", DOMAIN_DIR, "init", "--full")
        return self.graph_path.read_bytes()

    def empty_domain_graph(self, name="菜园"):
        path = self.tmp / "领域图.json"
        engine("--graph", path, "--kind", "domain", "init", "--empty", "--name", name)
        return path

    def write_proposal(self, modules, path=None, **extra):
        data = {"模块": modules}
        data.update(extra)
        (path or self.proposal_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sketch.main([str(a) for a in argv])
            except SystemExit as e:  # argparse 的用法错误
                code = e.code
        return Run(code, out.getvalue(), err.getvalue())

    def graph(self, path=None):
        return json.loads((path or self.graph_path).read_text(encoding="utf-8"))

    def titles(self, path=None):
        return {m["标题"]: [n["标题"] for n in m["节点"]] for m in self.graph(path)["模块"]}

    def node(self, title, path=None):
        for m in self.graph(path)["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("找不到节点「%s」" % title)


# ---------------------------------------------------------------- check：判重与回显，永不写

class CheckTest(SketchCase):
    def test_exact_duplicate_is_not_proposed_again(self):
        before = self.full_case_graph()
        self.write_proposal([{"标题": "养护", "节点": [{"标题": "浇水", "空白模板": "无"}, {"标题": "施追肥", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 0, r)
        self.assertIn("施追肥", r.out)
        self.assertIn("## 已在图里", r.out)
        new_section, existing_section = r.out.split("## 已在图里")
        self.assertNotIn("浇水", new_section, "同名节点不该再提")
        self.assertIn("浇水", existing_section)
        self.assertEqual(self.graph_path.read_bytes(), before, "check 不写图")

    def test_whitespace_and_punctuation_variants_count_as_same_title(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "养 护", "节点": [{"标题": "浇水。", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 0, r)
        self.assertIn("已在图里", r.out)
        self.assertNotIn("待定", r.out)

    def test_similar_but_different_title_is_listed_as_pending(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "整地", "节点": [{"标题": "施足底肥", "空白模板": "无"}]},
                             {"标题": "养护管理", "节点": [{"标题": "追肥", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 0, r)
        self.assertIn("待定", r.out)
        self.assertRegex(r.out, "施足底肥[^\\n]*施底肥")
        self.assertRegex(r.out, "养护管理[^\\n]*养护")

    def test_echo_lists_module_node_template_and_time_limit(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "越冬", "节点": [
            {"标题": "覆膜", "空白模板": "官方:覆膜记录.docx", "时限": "自霜降之日起 5 日内（指南，示例）"},
            {"标题": "清园", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 0, r)
        for text in ("越冬", "覆膜", "清园", "官方 覆膜记录.docx", "自霜降之日起 5 日内（指南，示例）"):
            self.assertIn(text, r.out)
        self.assertIn("案件图不存", r.out, "案件图上时限只回显，要说明不写入")

    def test_domain_same_name_is_marked_as_bring_in(self):
        engine("--graph", self.graph_path, "--domain", DOMAIN_DIR, "init", "--empty")
        self.write_proposal([{"标题": "整地", "节点": [{"标题": "松土", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path, "--domain", DOMAIN_DIR)
        self.assertEqual(r.code, 0, r)
        self.assertIn("领域图", r.out)
        self.assertRegex(r.out, "松土[^\\n]*带入")

    def test_duplicate_titles_inside_proposal_are_rejected(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}, {"标题": "覆膜", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 1, r)
        self.assertIn("覆膜", r.err)

    def test_malformed_proposal_is_rejected_with_exit_1(self):
        self.full_case_graph()
        self.proposal_path.write_text('{"模块": [{"标题": "越冬"}]}', encoding="utf-8")
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 1, r)
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "官方：x.docx"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 1, r)
        self.assertIn("空白模板", r.err)

    def test_missing_graph_is_rejected(self):
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path)
        self.assertEqual(r.code, 1, r)


# ---------------------------------------------------------------- apply：拍板后经引擎写入

class ApplyTest(SketchCase):
    def test_apply_writes_new_module_and_nodes_through_engine_and_views_follow(self):
        self.full_case_graph()
        self.write_proposal([
            {"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "官方:覆膜记录.docx", "时限": "自霜降之日起 5 日内（指南，示例）"},
                                   {"标题": "清园", "空白模板": "无"}]},
            {"标题": "养护", "节点": [{"标题": "浇水", "空白模板": "无"}, {"标题": "施追肥", "空白模板": "无"}]},
        ])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        titles = self.titles()
        self.assertEqual(titles["越冬"], ["覆膜", "清园"])
        self.assertEqual(titles["养护"], ["浇水", "除草", "搭架", "施追肥"], "同名的不重复加，新的追加在末尾")
        self.assertEqual(self.node("覆膜")["空白模板"], {"来源": "官方", "文件": "覆膜记录.docx"})
        self.assertNotIn("时限", self.node("覆膜"), "案件图不存时限（ADR-0016）")
        self.assertEqual(self.node("浇水")["id"], "n-jiaoshui", "已有节点原样不动")
        view = json.loads((self.tmp / "图视图.json").read_text(encoding="utf-8"))
        self.assertIn("越冬", [m["标题"] for m in view["模块"]])
        self.assertIn("施追肥", (self.tmp / "图视图.md").read_text(encoding="utf-8"))
        self.assertIn("越冬", r.out)
        self.assertIn("施追肥", r.out)

    def test_apply_refuses_while_pending_unresolved_and_writes_nothing(self):
        before = self.full_case_graph()
        self.write_proposal([{"标题": "整地", "节点": [{"标题": "施足底肥", "空白模板": "无"}, {"标题": "翻土", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE)
        self.assertEqual(r.code, 1, r)
        self.assertIn("施足底肥", r.err)
        self.assertEqual(self.graph_path.read_bytes(), before, "待定未定，一字不写")

    def test_pending_resolved_as_new_is_added(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "整地", "节点": [{"标题": "施足底肥", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE,
                     "--as-new", "施足底肥")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.titles()["整地"], ["松土", "施底肥", "施足底肥"])

    def test_pending_module_resolved_as_new(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "养护管理", "节点": [{"标题": "追肥", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE,
                     "--as-new", "养护管理")
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.titles()["养护管理"], ["追肥"])

    def test_as_new_must_name_a_pending_title(self):
        before = self.full_case_graph()
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE,
                     "--as-new", "覆膜")
        self.assertEqual(r.code, 1, r)
        self.assertIn("覆膜", r.err)
        self.assertEqual(self.graph_path.read_bytes(), before)

    def test_apply_brings_domain_node_in_by_domain_id(self):
        engine("--graph", self.graph_path, "--domain", DOMAIN_DIR, "init", "--empty")
        self.write_proposal([{"标题": "整地", "节点": [{"标题": "松土", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--domain", DOMAIN_DIR,
                     "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.node("松土")["id"], "n-songtu", "与领域图同名的按领域图带入，id 沿用")
        self.assertEqual(self.titles(), {"整地": ["松土"]}, "严格惰性：不带同模块其他节点")

    def test_apply_nothing_new_is_a_noop(self):
        before = self.full_case_graph()
        self.write_proposal([{"标题": "养护", "节点": [{"标题": "浇水", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.graph_path.read_bytes(), before)
        self.assertIn("没有", r.out)

    def test_apply_on_domain_graph_keeps_id_and_time_limit(self):
        path = self.empty_domain_graph()
        self.write_proposal([{"标题": "整地", "id": "m-zhengdi", "节点": [
            {"标题": "松土", "id": "n-songtu", "空白模板": "无"},
            {"标题": "施底肥", "id": "n-difei", "空白模板": "官方:施肥记录.docx", "时限": "自松土完成之日起 3 日内（手册，示例）"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", path, "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        data = self.graph(path)
        self.assertEqual(data["模块"][0]["id"], "m-zhengdi")
        self.assertEqual([n["id"] for n in data["模块"][0]["节点"]], ["n-songtu", "n-difei"])
        self.assertEqual(data["模块"][0]["节点"][1]["时限"], "自松土完成之日起 3 日内（手册，示例）")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["雏形.json", "领域图.json"], "领域图不出视图")

    def test_id_in_proposal_is_rejected_on_case_graph(self):
        before = self.full_case_graph()
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "id": "n-fumo", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", ENGINE)
        self.assertEqual(r.code, 1, r)
        self.assertIn("id", r.err)
        self.assertEqual(self.graph_path.read_bytes(), before)

    def test_domain_node_under_wrong_module_is_refused_before_writing(self):
        self.full_case_graph()
        # 「下种」在领域图里属于「播种」；改掉图里的标题让它不在图里，再提到「越冬」下
        engine("--graph", self.graph_path, "--domain", DOMAIN_DIR, "rename-node", "--node", "n-xiazhong", "--title", "播种入土")
        before = self.graph_path.read_bytes()
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "下种", "空白模板": "无"}, {"标题": "清园", "空白模板": "无"}]}])
        r = self.cli("check", "--proposal", self.proposal_path, "--graph", self.graph_path, "--domain", DOMAIN_DIR)
        self.assertEqual(r.code, 0, r)
        self.assertRegex(r.out, "下种[^\\n]*播种")
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--domain", DOMAIN_DIR,
                     "--engine", ENGINE)
        self.assertEqual(r.code, 1, r)
        self.assertIn("下种", r.err)
        self.assertEqual(self.graph_path.read_bytes(), before, "写之前能判出来的拒因，一字不写")

    def test_engine_rejection_mid_write_is_reported_and_exit_1(self):
        path = self.tmp / "领域图.json"
        shutil.copy(DOMAIN_DIR / "领域图.json", path)
        # 覆膜 借用了领域图里已有的 id，引擎会拒这一条；清园照写
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "id": "n-songtu", "空白模板": "无"},
                                                   {"标题": "清园", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", path, "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 1, r)
        self.assertIn("覆膜", r.err)
        self.assertEqual(self.titles(path)["越冬"], ["清园"], "拒的那条之外照写，回显里逐条说明")

    def test_missing_engine_is_a_clear_error(self):
        self.full_case_graph()
        self.write_proposal([{"标题": "越冬", "节点": [{"标题": "覆膜", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.graph_path, "--engine", self.tmp / "no.py")
        self.assertEqual(r.code, 1, r)
        self.assertIn("引擎", r.err)


# ---------------------------------------------------------------- from-case：回流候选（ADR-0012）

class FromCaseTest(SketchCase):
    def test_candidates_are_case_origin_nodes_with_a_confirmed_version(self):
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "add-module", "--title", "越冬")
        engine(*g, "add-node", "--module", "越冬", "--title", "覆膜", "--template", "官方:覆膜记录.docx")
        engine(*g, "add-node", "--module", "越冬", "--title", "清园", "--template", "生成:清园清单.docx")
        engine(*g, "add-node", "--module", "养护", "--title", "施追肥")
        engine(*g, "add-node", "--module", "养护", "--title", "松绑")
        for title in ("覆膜", "清园", "施追肥"):
            engine(*g, "generate", "--node", title, "--doc", "文书/%s/%s-v1.docx" % (title, title),
                   "--review", "文书/%s/%s-v1-审查报告.md" % (title, title))
        engine(*g, "confirm", "--node", "覆膜", "--words", "确认 覆膜")
        engine(*g, "confirm", "--node", "清园", "--words", "确认 清园")
        engine(*g, "generate", "--node", "清园", "--doc", "文书/清园/清园-v2.docx", "--review", "文书/清园/清园-v2-审查报告.md")
        out_path = self.tmp / "回流.json"
        r = self.cli("from-case", "--case", self.graph_path, "--domain", DOMAIN_DIR, "--out", out_path)
        self.assertEqual(r.code, 0, r)
        proposal = json.loads(out_path.read_text(encoding="utf-8"))
        by_title = {m["标题"]: m for m in proposal["模块"]}
        self.assertEqual(sorted(by_title), ["越冬"], "施追肥只生成未确认、松绑未生成，都不是候选；养护于是没有候选")
        self.assertEqual(by_title["越冬"]["id"].startswith("m-"), True)
        nodes = {n["标题"]: n for n in by_title["越冬"]["节点"]}
        self.assertEqual(sorted(nodes), ["清园", "覆膜"])
        self.assertEqual(nodes["覆膜"]["空白模板"], "官方:覆膜记录.docx")
        self.assertEqual(nodes["清园"]["空白模板"], "无", "生成空白模板不回流（ADR-0012）")
        self.assertTrue(nodes["覆膜"]["id"].startswith("n-"), "保留原 id")
        self.assertNotIn("时限", nodes["覆膜"])
        self.assertIn("覆膜", r.out)

    def test_node_added_under_domain_module_uses_domain_module_title(self):
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "rename-module", "--module", "养护", "--title", "养护（本案）")
        engine(*g, "add-node", "--module", "养护（本案）", "--title", "施追肥")
        engine(*g, "generate", "--node", "施追肥", "--doc", "文书/施追肥/施追肥-v1.docx", "--review", "文书/施追肥/施追肥-v1-审查报告.md")
        engine(*g, "confirm", "--node", "施追肥", "--words", "确认")
        out_path = self.tmp / "回流.json"
        r = self.cli("from-case", "--case", self.graph_path, "--domain", DOMAIN_DIR, "--out", out_path)
        self.assertEqual(r.code, 0, r)
        proposal = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual([m["标题"] for m in proposal["模块"]], ["养护"], "已在领域图里的模块按领域图标题指认，不带案件改名")
        self.assertEqual(proposal["模块"][0]["id"], "m-yanghu")
        self.assertEqual([n["标题"] for n in proposal["模块"][0]["节点"]], ["施追肥"])

    def test_confirmed_then_not_applicable_is_not_a_candidate(self):
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "add-node", "--module", "养护", "--title", "施追肥")
        engine(*g, "generate", "--node", "施追肥", "--doc", "文书/施追肥/施追肥-v1.docx", "--review", "文书/施追肥/施追肥-v1-审查报告.md")
        engine(*g, "confirm", "--node", "施追肥", "--words", "确认")
        engine(*g, "generate", "--node", "施追肥", "--doc", "文书/施追肥/施追肥-v2.docx", "--review", "文书/施追肥/施追肥-v2-审查报告.md")
        engine(*g, "not-applicable", "--node", "施追肥", "--words", "不适用")
        r = self.cli("from-case", "--case", self.graph_path, "--domain", DOMAIN_DIR)
        self.assertEqual(r.code, 0, r)
        self.assertIn("没有", r.out, "末态不适用的节点不是候选（ADR-0012）")

    def test_from_case_and_check_leave_both_graphs_untouched(self):
        """拍板前领域图一字不动（ADR-0012）：算候选与判重都只读，两张图的字节都不能变。"""
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "add-node", "--module", "养护", "--title", "施本案专用追肥")
        engine(*g, "generate", "--node", "施本案专用追肥", "--doc", "文书/追肥/追肥-v1.docx",
               "--review", "文书/追肥/追肥-v1-审查报告.md")
        engine(*g, "confirm", "--node", "施本案专用追肥", "--words", "确认")
        domain_copy = self.tmp / "领域图.json"
        shutil.copy(DOMAIN_DIR / "领域图.json", domain_copy)
        case_before, domain_before = self.graph_path.read_bytes(), domain_copy.read_bytes()
        out_path = self.tmp / "回流.json"
        r = self.cli("from-case", "--case", self.graph_path, "--domain", domain_copy, "--out", out_path)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.graph_path.read_bytes(), case_before, "from-case 不写案件图")
        self.assertEqual(domain_copy.read_bytes(), domain_before, "from-case 不写领域图")
        r = self.cli("check", "--proposal", out_path, "--graph", domain_copy, "--kind", "domain")
        self.assertEqual(r.code, 0, r)
        self.assertIn("施本案专用追肥", r.out)
        self.assertEqual(domain_copy.read_bytes(), domain_before, "check --kind domain 不写领域图")
        self.assertEqual(self.graph_path.read_bytes(), case_before, "回流全程只读案件图")

    def test_case_graph_of_another_domain_is_refused(self):
        self.full_case_graph()
        other = self.tmp / "别的领域"
        other.mkdir()
        engine("--graph", other / "领域图.json", "--kind", "domain", "init", "--empty", "--name", "果园")
        r = self.cli("from-case", "--case", self.graph_path, "--domain", other)
        self.assertEqual(r.code, 1, r)
        self.assertIn("果园", r.err)

    def test_no_candidates_writes_nothing_and_says_so(self):
        self.full_case_graph()
        out_path = self.tmp / "回流.json"
        r = self.cli("from-case", "--case", self.graph_path, "--domain", DOMAIN_DIR, "--out", out_path)
        self.assertEqual(r.code, 0, r)
        self.assertFalse(out_path.exists())
        self.assertIn("没有", r.out)

    def test_reflux_round_trip_into_domain_graph_keeps_ids(self):
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "add-module", "--title", "越冬")
        engine(*g, "add-node", "--module", "越冬", "--title", "覆膜")
        engine(*g, "generate", "--node", "覆膜", "--doc", "文书/覆膜/覆膜-v1.docx", "--review", "文书/覆膜/覆膜-v1-审查报告.md")
        engine(*g, "confirm", "--node", "覆膜", "--words", "确认")
        case_ids = {self.node("覆膜")["id"], next(m["id"] for m in self.graph()["模块"] if m["标题"] == "越冬")}
        out_path = self.tmp / "回流.json"
        self.cli("from-case", "--case", self.graph_path, "--domain", DOMAIN_DIR, "--out", out_path)
        domain_copy = self.tmp / "领域图.json"
        shutil.copy(DOMAIN_DIR / "领域图.json", domain_copy)
        r = self.cli("apply", "--proposal", out_path, "--graph", domain_copy, "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        data = self.graph(domain_copy)
        m = next(m for m in data["模块"] if m["标题"] == "越冬")
        self.assertEqual({m["id"], m["节点"][0]["id"]}, case_ids, "回流保留案件里的原 id")


# ---------------------------------------------------------------- 两条路的终点都是活图（ADR-0020）

class LiveGraphIsTheTargetTest(SketchCase):
    """开发侧那两条路写的也是活图（#102 验收，ADR-0020）：`home` 回显的那个目录是 `apply` 的落点，
    包内出厂种子一个字节不动。

    种子一律用临时的假包（目录名摆成 `<...>/domain/assets/<领域名>`，判据 ②），
    与 tests/graph/test_package_guard.py 同一个理由：拿真包测就是拿开发者的工作树赌一次规则，
    规则坏了它会被写脏。真包落在判据 ① 射程里由那份测试钉住。
    """

    def setUp(self):
        super().setUp()
        self.seed_root = self.tmp / "domain" / "assets"
        (self.seed_root / "菜园").mkdir(parents=True)
        self.seed = self.seed_root / "菜园" / "领域图.json"
        shutil.copy(DOMAIN_DIR / "领域图.json", self.seed)
        self.live_root = self.tmp / "活图根" / "领域"

    def home(self):
        r = self.cli("home", "--name", "菜园", "--live-root", self.live_root, "--seed-root", self.seed_root)
        self.assertEqual(r.code, 0, r)
        第一行 = r.out.splitlines()[0]
        self.assertTrue(第一行.startswith("活图："), "home 的第一行该是活图路径：%r" % 第一行)
        return pathlib.Path(第一行.split("：", 1)[1])

    def test_apply_writes_the_live_graph_home_echoes_and_leaves_the_seed_untouched(self):
        live = self.home()
        种子字节 = self.seed.read_bytes()
        self.write_proposal([{"标题": "养护", "id": "m-yanghu", "节点": [
            {"标题": "补种", "id": "n-buzhong", "空白模板": "无"},
            {"标题": "打顶", "id": "n-dading", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", live / "领域图.json",
                     "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.titles(live / "领域图.json")["养护"],
                         ["浇水", "除草", "搭架", "补种", "打顶"], "活图该多出那两条")
        self.assertEqual(self.seed.read_bytes(), 种子字节,
                         "开发侧那条路写的是活图，包内出厂种子一个字节都不该动（ADR-0020）")

    def test_the_same_apply_aimed_at_the_seed_is_refused_by_the_engine(self):
        """上一条那个「种子字节不变」不是因为没人写它：同一份雏形冲着种子跑，引擎无条件拒。"""
        self.home()
        种子字节 = self.seed.read_bytes()
        self.write_proposal([{"标题": "养护", "id": "m-yanghu", "节点": [
            {"标题": "补种", "id": "n-buzhong", "空白模板": "无"}]}])
        r = self.cli("apply", "--proposal", self.proposal_path, "--graph", self.seed,
                     "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 1, r)
        self.assertIn("ADR-0020", r.err, "引擎那条拒该被照抄出来：%r" % r.err)
        self.assertEqual(self.seed.read_bytes(), 种子字节)

    def test_from_case_against_the_live_graph_never_touches_the_seed(self):
        """补历史那条路：`from-case --domain <活图>`，算候选、判重、写入，终点都是活图。"""
        self.full_case_graph()
        g = ["--graph", self.graph_path, "--domain", DOMAIN_DIR]
        engine(*g, "add-node", "--module", "养护", "--title", "补种记录")
        engine(*g, "generate", "--node", "补种记录", "--doc", "文书/补种/补种-v1.docx",
               "--review", "文书/补种/补种-v1-审查报告.md")
        engine(*g, "confirm", "--node", "补种记录", "--words", "确认")
        case_id = self.node("补种记录")["id"]
        live = self.home()
        种子字节 = self.seed.read_bytes()
        out_path = self.tmp / "回流.json"
        r = self.cli("from-case", "--case", self.graph_path, "--domain", live, "--out", out_path)
        self.assertEqual(r.code, 0, r)
        r = self.cli("apply", "--proposal", out_path, "--graph", live / "领域图.json",
                     "--kind", "domain", "--engine", ENGINE)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.node("补种记录", live / "领域图.json")["id"], case_id,
                         "回流保留案件里的原 id（ADR-0012）")
        self.assertEqual(self.seed.read_bytes(), 种子字节, "补历史那条路也不碰出厂种子")


# ---------------------------------------------------------------- docx-text：整读指南与手册

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>种植</w:t></w:r><w:r><w:t>指南</w:t></w:r></w:p>
<w:p/>
<w:p/>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>节点</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>表格</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>覆膜</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>覆膜记录</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:t>清园应及时。</w:t></w:r></w:p>
<w:sectPr/></w:body></w:document>"""


class DocxTextTest(SketchCase):
    def make_docx(self, xml=DOCUMENT_XML):
        path = self.tmp / "指南.docx"
        with zipfile.ZipFile(str(path), "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("word/document.xml", xml)
        return path

    def test_paragraphs_and_table_rows_come_out_as_lines(self):
        r = self.cli("docx-text", self.make_docx())
        self.assertEqual(r.code, 0, r)
        self.assertEqual(r.out, "种植指南\n\n节点 | 表格\n覆膜 | 覆膜记录\n清园应及时。\n")

    def test_real_handbooks_are_readable(self):
        handbooks = sorted((REPO / "skills" / "in-progress" / "domain" / "assets" / "破产" / "指引手册").glob("*.docx"))
        self.assertEqual(len(handbooks), 2)
        for h in handbooks:
            r = self.cli("docx-text", h)
            self.assertEqual(r.code, 0, r.err)
            self.assertGreater(len(r.out), 5000, "%s 读出来太短" % h.name)

    def test_not_a_docx_is_rejected(self):
        bad = self.tmp / "x.docx"
        bad.write_bytes(b"not a zip")
        r = self.cli("docx-text", bad)
        self.assertEqual(r.code, 1, r)
        r = self.cli("docx-text", self.tmp / "missing.docx")
        self.assertEqual(r.code, 1, r)


if __name__ == "__main__":
    unittest.main()
