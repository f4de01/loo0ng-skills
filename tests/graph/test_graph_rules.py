"""引擎的规则面：条目与状态、拒写、原子写、惰性带入、构成操作、领域图编辑、派生视图、真实子进程。

运行：python -m unittest discover -s tests/graph -p 'test_*.py'
共用 test_graph.py 里的 EngineCase（临时工作区 + cli()），领域一律是合成小领域。
"""
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_graph import DOMAIN, SCRIPT, EngineCase, graph  # noqa: E402


# ---------------------------------------------------------------- 条目与状态

class EntryTest(EngineCase):
    def setUp(self):
        super().setUp()
        self.ok("init", "--full")

    def test_states_follow_last_entry(self):
        self.assertEqual(graph.node_state(self.node("松土")), "未生成")
        self.ok("generate", "--node", "松土", "--doc", "文书/松土/松土-v1.docx", "--source", "文书/松土/松土-v1.md",
                "--review", "文书/松土/松土-v1-审查报告.md")
        self.assertEqual(graph.node_state(self.node("松土")), "已生成")
        self.ok("confirm", "--node", "松土", "--words", "确认 松土")
        self.assertEqual(graph.node_state(self.node("松土")), "已确认")
        self.ok("generate", "--node", "松土", "--doc", "文书/松土/松土-v2.docx", "--review", "文书/松土/松土-v2-审查报告.md")
        n = self.node("松土")
        self.assertEqual(graph.node_state(n), "已生成")
        self.assertEqual([e["动作"] for e in n["条目"]], ["生成", "确认", "生成"], "旧的确认留在历史里")
        self.assertEqual(n["条目"][1]["原话"], "确认 松土")

    def test_generate_entry_fields_and_source_inferred(self):
        self.ok("generate", "--node", "施底肥", "--doc", "a.docx", "--source", "a.md", "--review", "a-审查报告.md")
        e = self.node("施底肥")["条目"][0]
        self.assertEqual({k: e[k] for k in ("动作", "来源", "文书", "源", "审查报告")},
                         {"动作": "生成", "来源": "agent", "文书": "a.docx", "源": "a.md", "审查报告": "a-审查报告.md"})
        self.assertRegex(e["时间"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

    def test_lawyer_written_generate_records_lawyer_as_source(self):
        self.ok("generate", "--node", "浇水", "--doc", "b.docx", "--review", "b-审查报告.md", "--lawyer-written")
        e = self.node("浇水")["条目"][0]
        self.assertEqual(e["来源"], "律师")
        self.assertNotIn("源", e)

    def test_not_applicable_is_terminal(self):
        self.ok("not-applicable", "--node", "搭架", "--words", "搭架 不适用")
        n = self.node("搭架")
        self.assertEqual(graph.node_state(n), "不适用")
        self.assertEqual(n["条目"][0]["来源"], "律师")
        self.rejected("generate", "--node", "搭架", "--doc", "c.docx", "--review", "c-审查报告.md")
        self.rejected("not-applicable", "--node", "搭架", "--words", "再来一次")

    def test_confirmed_cannot_be_not_applicable(self):
        self.ok("generate", "--node", "松土", "--doc", "a.docx", "--review", "a-审查报告.md")
        self.ok("confirm", "--node", "松土", "--words", "确认")
        r = self.rejected("not-applicable", "--node", "松土", "--words", "松土 不适用")
        self.assertIn("已确认", r.err)
        self.assertEqual(len(self.node("松土")["条目"]), 2)

    def test_confirm_needs_a_generated_document(self):
        self.rejected("confirm", "--node", "松土", "--words", "确认")
        self.ok("generate", "--node", "松土", "--doc", "a.docx", "--review", "a-审查报告.md")
        self.ok("confirm", "--node", "松土", "--words", "确认")
        self.rejected("confirm", "--node", "松土", "--words", "再确认一次")

    def test_no_edit_or_delete_subcommands(self):
        """引擎没有改条目、删条目、删节点的操作：这些名字都是用法错误（退出码 2）。"""
        for bad in ("edit-entry", "delete-entry", "remove-entry", "delete-node", "remove-node"):
            self.assertEqual(self.cli(bad, "--node", "松土").code, 2, bad)

    def test_generate_paths_must_be_relative_forward_slash(self):
        for bad in ("C:/x/a.docx", "文书\\松土\\a.docx", "../a.docx", "/a.docx"):
            r = self.rejected("generate", "--node", "松土", "--doc", bad, "--review", "b.md")
            self.assertIn("相对", r.err, bad)
        self.assertEqual(self.node("松土")["条目"], [])

    def test_entries_in_domain_kind_are_refused(self):
        dom = self.tmp / "领域图.json"
        kw = dict(kind="domain", domain=False, graph_path=dom)
        self.ok("init", "--empty", "--name", "试验", **kw)
        self.ok("add-module", "--title", "甲", **kw)
        self.ok("add-node", "--module", "甲", "--title", "甲一", **kw)
        self.rejected("generate", "--node", "甲一", "--doc", "a.docx", "--review", "b.md", **kw)


class ModuleNotApplicableTest(EngineCase):
    def test_expands_domain_module_into_graph_and_marks_each(self):
        self.ok("init", "--empty")
        self.ok("not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        self.assertEqual(self.titles("养护"), ["浇水", "除草", "搭架"])
        for n in self.module("养护")["节点"]:
            self.assertEqual(graph.node_state(n), "不适用")
            self.assertEqual(n["条目"][0]["原话"], "模块 养护 不适用")
        self.assertEqual(self.module_titles(), ["养护"], "只带入这个模块，不带别的")
        self.assertEqual(graph.module_state(self.module("养护")), "不适用")

    def test_also_marks_lawyer_added_nodes_and_skips_already_na(self):
        self.ok("init", "--empty")
        self.ok("add-node", "--module", "养护", "--title", "松绑")
        self.ok("not-applicable", "--node", "除草", "--words", "除草 不适用")
        self.ok("not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        self.assertEqual(self.titles("养护"), ["松绑", "浇水", "除草", "搭架"], "律师先加的节点位置不动，领域节点按领域序跟在后面")
        self.assertEqual(len(self.node("除草")["条目"]), 1, "已是不适用的不再追加")
        self.assertEqual(graph.node_state(self.node("松绑")), "不适用")

    def test_refused_when_a_node_is_confirmed(self):
        self.ok("init", "--full")
        self.ok("generate", "--node", "浇水", "--doc", "a.docx", "--review", "b.md")
        self.ok("confirm", "--node", "浇水", "--words", "确认")
        self.rejected("not-applicable", "--module", "养护", "--words", "模块 养护 不适用")
        self.assertEqual(graph.node_state(self.node("除草")), "未生成", "整个操作不落盘")


# ---------------------------------------------------------------- 原子写与拒写不动文件

class AtomicWriteTest(EngineCase):
    def test_rejected_write_leaves_files_byte_identical(self):
        self.ok("init", "--full")
        before = {p.name: p.read_bytes() for p in self.tmp.iterdir()}
        self.rejected("delete-module", "--module", "整地")
        after = {p.name: p.read_bytes() for p in self.tmp.iterdir()}
        self.assertEqual(before, after)

    def test_successful_write_leaves_no_temp_files(self):
        self.ok("init", "--full")
        self.ok("add-module", "--title", "甲")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["图.json", "图视图.json", "图视图.md"])

    def test_failed_replace_keeps_original(self):
        self.ok("init", "--full")
        before = self.graph_path.read_bytes()
        with mock.patch.object(graph.os, "replace", side_effect=OSError("模拟替换失败")):
            with self.assertRaises(OSError):
                self.cli("add-module", "--title", "甲")
        self.assertEqual(self.graph_path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["图.json", "图视图.json", "图视图.md"])


# ---------------------------------------------------------------- 惰性带入与插入位置

class LazyCreationTest(EngineCase):
    def test_generate_on_absent_node_brings_node_and_module_only(self):
        self.ok("init", "--empty")
        r = self.ok("generate", "--node", "下种", "--doc", "a.docx", "--review", "b.md")
        self.assertIn("带入", r.out)
        self.assertEqual(self.module_titles(), ["播种"])
        self.assertEqual(self.titles("播种"), ["下种"], "不带同模块其他节点")
        n = self.node("下种")
        self.assertEqual(n["id"], "n-xiazhong")
        self.assertNotIn("时限", n)
        self.assertEqual(n["空白模板"], {"来源": "官方", "文件": "播种登记.docx"})

    def test_absent_everywhere_is_refused(self):
        self.ok("init", "--empty")
        r = self.rejected("generate", "--node", "不存在的节点", "--doc", "a.docx", "--review", "b.md")
        self.assertIn("领域图里也没有", r.err)

    def test_node_inserted_by_domain_relative_order_between_siblings(self):
        self.ok("init", "--empty")
        self.ok("generate", "--node", "搭架", "--doc", "a.docx", "--review", "b.md")
        self.ok("add-node", "--module", "养护", "--title", "律师加的")
        self.ok("generate", "--node", "浇水", "--doc", "c.docx", "--review", "d.md")
        self.assertEqual(self.titles("养护"), ["浇水", "搭架", "律师加的"])
        self.ok("generate", "--node", "除草", "--doc", "e.docx", "--review", "f.md")
        self.assertEqual(self.titles("养护"), ["浇水", "除草", "搭架", "律师加的"], "律师自加节点位置不动")

    def test_module_inserted_by_domain_relative_order(self):
        self.ok("init", "--empty")
        self.ok("generate", "--node", "采摘", "--doc", "a.docx", "--review", "b.md")
        self.ok("add-module", "--title", "律师加的模块")
        self.ok("generate", "--node", "松土", "--doc", "c.docx", "--review", "d.md")
        self.ok("generate", "--node", "浇水", "--doc", "e.docx", "--review", "f.md")
        self.assertEqual(self.module_titles(), ["整地", "养护", "收获", "律师加的模块"])

    def test_add_node_with_domain_title_brings_domain_node_not_duplicate(self):
        self.ok("init", "--empty")
        self.ok("add-node", "--module", "播种", "--title", "下种")
        self.assertEqual(self.node("下种")["id"], "n-xiazhong")
        ahead = {m["标题"]: m for m in self.view_json()["前方"]}
        self.assertEqual([n["标题"] for n in ahead["播种"]["节点"]], ["选种"], "前方里不再有下种")

    def test_without_domain_nothing_is_created(self):
        self.ok("init", "--empty", "--name", "试验", domain=False)
        self.rejected("generate", "--node", "下种", "--doc", "a.docx", "--review", "b.md", domain=False)


# ---------------------------------------------------------------- 构成操作

class CompositionTest(EngineCase):
    def setUp(self):
        super().setUp()
        self.ok("init", "--full")

    def test_rename_keeps_id_and_entries(self):
        self.ok("generate", "--node", "下种", "--doc", "a.docx", "--review", "b.md")
        self.ok("rename-node", "--node", "下种", "--title", "播种入土")
        n = self.node("播种入土")
        self.assertEqual(n["id"], "n-xiazhong")
        self.assertEqual(len(n["条目"]), 1)
        self.rejected("rename-node", "--node", "播种入土", "--title", "选种")

    def test_move_node_across_modules_and_order(self):
        self.ok("move-node", "--node", "搭架", "--module", "播种", "--first")
        self.assertEqual(self.titles("播种"), ["搭架", "选种", "下种"])
        self.assertEqual(self.titles("养护"), ["浇水", "除草"])
        self.ok("move-node", "--node", "搭架", "--after", "选种")
        self.assertEqual(self.titles("播种"), ["选种", "搭架", "下种"])
        self.rejected("move-node", "--node", "搭架", "--before", "浇水")

    def test_module_rename_move_delete(self):
        self.ok("rename-module", "--module", "养护", "--title", "照料")
        self.ok("move-module", "--module", "照料", "--first")
        self.assertEqual(self.module_titles(), ["照料", "整地", "播种", "收获"])
        r = self.rejected("delete-module", "--module", "照料")
        self.assertIn("节点永不删", r.err)
        for t in ("浇水", "除草", "搭架"):
            self.ok("move-node", "--node", t, "--module", "收获")
        self.ok("delete-module", "--module", "照料")
        self.assertEqual(self.module_titles(), ["整地", "播种", "收获"])
        self.assertEqual(self.titles("收获"), ["采摘", "记账", "浇水", "除草", "搭架"], "节点一个不丢")

    def test_set_template(self):
        self.ok("set-template", "--node", "松土", "--template", "生成:松土记录.docx")
        self.assertEqual(self.node("松土")["空白模板"], {"来源": "生成", "文件": "松土记录.docx"})
        self.ok("set-template", "--node", "松土", "--template", "无")
        self.assertEqual(self.node("松土")["空白模板"], "无")
        self.rejected("set-template", "--node", "松土", "--template", "别的:x.docx")

    def test_time_limit_cannot_be_set_on_case_graph(self):
        r = self.rejected("set-time-limit", "--node", "松土", "--time-limit", "三日内")
        self.assertIn("时限", r.err)
        self.rejected("add-node", "--module", "整地", "--title", "新的", "--time-limit", "三日内")

    def test_explicit_id_only_for_domain_graph(self):
        """案件图里 id 由引擎生成；给 --id 冒用领域图 id 会让来源与时限被冒名，所以拒。"""
        r = self.rejected("add-node", "--module", "播种", "--title", "自加", "--id", "n-difei")
        self.assertIn("--id", r.err)
        self.rejected("add-module", "--title", "自加模块", "--id", "m-x")


class DomainKindTest(EngineCase):
    """开发者用同一引擎编辑领域图：可带时限、无条目、不出视图。"""

    def test_build_domain_graph_with_deadlines_and_no_views(self):
        dom = self.tmp / "领域图.json"
        kw = dict(kind="domain", domain=False, graph_path=dom)
        self.ok("init", "--empty", "--name", "试验", **kw)
        self.ok("add-module", "--title", "甲", "--id", "m-jia", **kw)
        self.ok("add-node", "--module", "甲", "--title", "甲一", "--id", "n-jia1", "--time-limit", "三日内（示例）", **kw)
        self.ok("add-node", "--module", "甲", "--title", "甲二", **kw)
        self.ok("set-time-limit", "--node", "甲二", "--time-limit", "五日内（示例）", **kw)
        self.ok("set-time-limit", "--node", "甲一", **kw)
        data = self.read(dom)
        self.assertEqual(data["领域"], "试验")
        self.assertNotIn("时限", data["模块"][0]["节点"][0])
        self.assertEqual(data["模块"][0]["节点"][1]["时限"], "五日内（示例）")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["领域图.json"], "领域目录不出视图")
        self.ok("validate", **kw)
        r = self.cli("--domain", str(dom), "init", "--full", domain=False)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.view_node("甲二")["时限"], "五日内（示例）")

    def test_domain_directory_is_accepted_for_domain_arg(self):
        r = self.cli("--domain", str(DOMAIN.parent), "init", "--full", domain=False)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.module_titles(), ["整地", "播种", "养护", "收获"])


# ---------------------------------------------------------------- 派生视图、前方、来源、时限

class ViewTest(EngineCase):
    def test_full_start_with_deadlines(self):
        """验收：带时限的领域图整份起手，前方为空，每个节点 来源 领域图，时限句原样带出。"""
        self.ok("init", "--full")
        view = self.view_json()
        self.assertEqual(view["前方"], [])
        self.assertEqual(view["格式版本"], self.read()["格式版本"])
        self.assertEqual(view["领域"], "菜园")
        self.assertEqual(view["源图"], "图.json")
        self.assertIn("生成时间", view)
        for m in view["模块"]:
            self.assertEqual(m["来源"], "领域图")
            self.assertEqual(m["状态"], "进行中")
            for n in m["节点"]:
                self.assertEqual(n["来源"], "领域图")
                self.assertEqual(n["状态"], "未生成")
        self.assertEqual(self.view_node("施底肥")["时限"], "自松土完成之日起 3 日内（手册，示例）")
        self.assertEqual(self.view_node("记账")["时限"], "自采摘结束之日起 7 日内（手册，示例）")
        self.assertNotIn("时限", self.view_node("松土"))
        md = self.view_md()
        self.assertIn("自松土完成之日起 3 日内（手册，示例）", md)
        self.assertIn("来源 领域图", md)

    def test_lawyer_added_node_has_case_origin_and_no_deadline(self):
        self.ok("init", "--full")
        self.ok("add-node", "--module", "整地", "--title", "翻晒")
        n = self.view_node("翻晒")
        self.assertEqual(n["来源"], "案件")
        self.assertNotIn("时限", n)
        self.assertEqual(n["状态"], "未生成")
        self.assertIn("来源 案件", self.view_md())
        self.ok("add-module", "--title", "记录")
        self.assertEqual([m for m in self.view_json()["模块"] if m["标题"] == "记录"][0]["来源"], "案件")

    def test_ahead_lists_missing_modules_and_nodes_with_deadlines(self):
        self.ok("init", "--empty")
        self.ok("generate", "--node", "下种", "--doc", "a.docx", "--review", "b.md")
        view = self.view_json()
        ahead = {m["标题"]: m for m in view["前方"]}
        self.assertEqual(list(ahead), ["整地", "播种", "养护", "收获"])
        self.assertEqual(ahead["整地"]["状态"], "尚未进图")
        self.assertEqual(ahead["播种"]["状态"], "已进图", "模块已进图，前方只列它没进图的节点")
        self.assertEqual([n["标题"] for n in ahead["播种"]["节点"]], ["选种"])
        self.assertEqual(ahead["整地"]["节点"][1]["时限"], "自松土完成之日起 3 日内（手册，示例）")
        for m in view["前方"]:
            self.assertEqual(m["来源"], "领域图")
            for n in m["节点"]:
                self.assertEqual((n["来源"], n["状态"]), ("领域图", "尚未进图"))
                self.assertIn("空白模板", n)
        md = self.view_md()
        self.assertIn("## 前方", md)
        self.assertIn("选种（尚未进图", md)

    def test_ahead_empty_without_domain(self):
        self.ok("init", "--empty", "--name", "试验", domain=False)
        self.ok("add-module", "--title", "甲", domain=False)
        view = self.view_json()
        self.assertEqual(view["前方"], [])
        self.assertEqual(view["模块"][0]["来源"], "案件")

    def test_views_recomputed_on_every_write_and_carry_entries_and_versions(self):
        self.ok("init", "--full")
        self.ok("generate", "--node", "松土", "--doc", "文书/松土/松土-v1.docx", "--source", "文书/松土/松土-v1.md",
                "--review", "文书/松土/松土-v1-审查报告.md")
        self.ok("confirm", "--node", "松土", "--words", "确认 松土，可以报")
        n = self.view_node("松土")
        self.assertEqual(n["状态"], "已确认")
        self.assertEqual(n["文书版本"], [{"版本": 1, "文书": "文书/松土/松土-v1.docx", "源": "文书/松土/松土-v1.md",
                                          "审查报告": "文书/松土/松土-v1-审查报告.md",
                                          "时间": n["条目"][0]["时间"], "来源": "agent"}])
        self.assertEqual(n["条目"][1]["原话"], "确认 松土，可以报")
        self.assertIn("「确认 松土，可以报」", self.view_md())
        self.ok("generate", "--node", "松土", "--doc", "文书/松土/松土-v2.docx", "--review", "文书/松土/松土-v2-审查报告.md")
        n = self.view_node("松土")
        self.assertEqual(n["状态"], "已生成")
        self.assertEqual([v["版本"] for v in n["文书版本"]], [1, 2])

    def test_module_states(self):
        self.ok("init", "--full")
        self.ok("not-applicable", "--module", "养护", "--words", "养护 不适用")
        for t in ("松土", "施底肥"):
            self.ok("generate", "--node", t, "--doc", t + ".docx", "--review", t + "-审查报告.md")
        self.ok("confirm", "--node", "松土", "--words", "确认")
        self.ok("not-applicable", "--node", "施底肥", "--words", "不适用")
        states = {m["标题"]: m["状态"] for m in self.view_json()["模块"]}
        self.assertEqual(states, {"整地": "已完成", "播种": "进行中", "养护": "不适用", "收获": "进行中"})

    def test_views_subcommand_refreshes_after_domain_change(self):
        self.ok("init", "--full")
        newer = self.tmp / "新领域图.json"
        dom = json.loads(DOMAIN.read_text(encoding="utf-8"))
        dom["模块"][0]["节点"].append({"id": "n-new", "标题": "新节点", "空白模板": "无", "条目": []})
        newer.write_text(json.dumps(dom, ensure_ascii=False), encoding="utf-8")
        before = self.graph_path.read_bytes()
        r = self.cli("--domain", str(newer), "views", domain=False)
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.graph_path.read_bytes(), before, "只重算视图，图一字不动")
        self.assertEqual(self.view_json()["前方"][0]["节点"][0]["标题"], "新节点")

    def test_no_em_dash_in_markdown_view(self):
        self.ok("init", "--full")
        self.ok("generate", "--node", "松土", "--doc", "a.docx", "--review", "b.md")
        self.assertNotIn(chr(0x2014), self.view_md(), "破折号不进视图")

    def test_format_version_shared_by_graph_and_view_and_checked_on_domain(self):
        self.ok("init", "--full")
        self.assertEqual(self.read()["格式版本"], self.view_json()["格式版本"])
        self.assertEqual(self.read()["格式版本"], graph.FORMAT_VERSION)
        odd = self.tmp / "旧领域图.json"
        dom = json.loads(DOMAIN.read_text(encoding="utf-8"))
        dom["格式版本"] = graph.FORMAT_VERSION + 1
        odd.write_text(json.dumps(dom, ensure_ascii=False), encoding="utf-8")
        r = self.cli("--domain", str(odd), "add-module", "--title", "甲", domain=False)
        self.assertEqual(r.code, 1, r)
        self.assertIn("格式版本", r.err)
        self.assertIn("领域图不合校验", r.err)
        self.assertNotIn("手改", r.err, "领域图的问题不该说成律师改了 图.json")


# ---------------------------------------------------------------- 真实子进程（中文参数与输出）

class SubprocessTest(EngineCase):
    def test_cli_runs_as_subprocess_with_chinese_arguments(self):
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        base = [sys.executable, str(SCRIPT), "--graph", str(self.graph_path), "--domain", str(DOMAIN)]

        def run(*extra):
            return subprocess.run(base + list(extra), capture_output=True, cwd=str(self.tmp), env=env)

        r = run("init", "--empty")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run("generate", "--node", "下种", "--doc", "文书/下种/下种-v1.docx", "--review", "文书/下种/下种-v1-审查报告.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("已追加生成条目", r.stdout.decode("utf-8"))
        self.assertEqual(self.node("下种")["条目"][0]["文书"], "文书/下种/下种-v1.docx")
        r = run("confirm", "--node", "松土", "--words", "确认")
        self.assertEqual(r.returncode, 1)
        self.assertIn("拒写", r.stderr.decode("utf-8"))
        self.assertEqual(run("bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
