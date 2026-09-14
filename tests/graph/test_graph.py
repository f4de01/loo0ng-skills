"""skills/engineering/graph/scripts/graph.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/graph/test_graph.py

缝是引擎 CLI 加工作区里的文件：每个测试在临时目录里调 main(argv)，再读 图.json 与两份视图断言。
领域一律用合成小领域 evals/领域/菜园/领域图.json，证明引擎不认破产语义（ADR-0015）。
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
SCRIPT = REPO / "skills" / "engineering" / "graph" / "scripts" / "graph.py"
DOMAIN = REPO / "evals" / "领域" / "菜园" / "领域图.json"

spec = importlib.util.spec_from_file_location("loo0ng_graph", SCRIPT)
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class EngineCase(unittest.TestCase):
    """每个测试一个临时工作区；cli() 默认对工作区里的 图.json 操作，并带上合成领域图。"""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="graph-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.graph_path = self.tmp / "图.json"

    def cli(self, *argv, domain=True, kind=None, graph_path=None):
        args = ["--graph", str(graph_path or self.graph_path)]
        if domain:
            args += ["--domain", str(DOMAIN)]
        if kind:
            args += ["--kind", kind]
        args += list(argv)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = graph.main(args)
            except SystemExit as e:  # argparse 的用法错误
                code = e.code
        return Run(code, out.getvalue(), err.getvalue())

    def ok(self, *argv, **kw):
        r = self.cli(*argv, **kw)
        self.assertEqual(r.code, 0, r)
        return r

    def rejected(self, *argv, **kw):
        r = self.cli(*argv, **kw)
        self.assertEqual(r.code, 1, r)
        return r

    def read(self, path=None):
        return json.loads((path or self.graph_path).read_text(encoding="utf-8"))

    def view_json(self):
        return json.loads((self.tmp / "图视图.json").read_text(encoding="utf-8"))

    def view_md(self):
        return (self.tmp / "图视图.md").read_text(encoding="utf-8")

    def node(self, title, data=None):
        data = data or self.read()
        for m in data["模块"]:
            for n in m["节点"]:
                if n["标题"] == title or n["id"] == title:
                    return n
        raise AssertionError("图里没有节点 %s" % title)

    def module(self, title, data=None):
        data = data or self.read()
        for m in data["模块"]:
            if m["标题"] == title or m["id"] == title:
                return m
        raise AssertionError("图里没有模块 %s" % title)

    def titles(self, module_title, data=None):
        return [n["标题"] for n in self.module(module_title, data)["节点"]]

    def module_titles(self, data=None):
        return [m["标题"] for m in (data or self.read())["模块"]]

    def view_node(self, title, view=None):
        view = view or self.view_json()
        for m in view["模块"]:
            for n in m["节点"]:
                if n["标题"] == title:
                    return n
        raise AssertionError("视图里没有节点 %s" % title)


# ---------------------------------------------------------------- 起手与校验

class InitTest(EngineCase):
    def test_empty_start_writes_graph_and_both_views(self):
        self.ok("init", "--empty")
        data = self.read()
        self.assertEqual(data, {"格式版本": graph.FORMAT_VERSION, "领域": "菜园", "模块": []})
        self.assertTrue((self.tmp / "图视图.md").is_file())
        self.assertTrue((self.tmp / "图视图.json").is_file())

    def test_empty_start_without_domain_needs_a_name(self):
        r = self.cli("init", "--empty", domain=False)
        self.assertNotEqual(r.code, 0)
        self.ok("init", "--empty", "--name", "试验", domain=False)
        self.assertEqual(self.read()["领域"], "试验")

    def test_full_start_copies_domain_graph_without_deadlines(self):
        self.ok("init", "--full")
        data = self.read()
        self.assertEqual(self.module_titles(data), ["整地", "播种", "养护", "收获"])
        self.assertEqual(self.titles("养护", data), ["浇水", "除草", "搭架"])
        self.assertEqual(self.node("施底肥", data)["id"], "n-difei")
        self.assertEqual(self.node("施底肥", data)["空白模板"], {"来源": "官方", "文件": "施肥记录.docx"})
        for m in data["模块"]:
            for n in m["节点"]:
                self.assertNotIn("时限", n, n)
                self.assertEqual(n["条目"], [])

    def test_init_refuses_when_graph_exists(self):
        self.ok("init", "--empty")
        self.rejected("init", "--empty")

    def test_init_from_custom_graph(self):
        custom = self.tmp / "定制.json"
        custom.write_text(json.dumps({"格式版本": graph.FORMAT_VERSION, "领域": "菜园", "模块": [
            {"id": "m-a", "标题": "甲", "节点": [{"id": "n-a", "标题": "甲一", "空白模板": "无", "条目": []}]}]},
            ensure_ascii=False), encoding="utf-8")
        self.ok("init", "--from", str(custom))
        self.assertEqual(self.module_titles(), ["甲"])


class ValidationTest(EngineCase):
    def write_raw(self, obj):
        self.graph_path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def test_invalid_file_is_refused_and_left_untouched(self):
        self.ok("init", "--empty")
        raw = self.read()
        raw["状态"] = "乱写"
        self.write_raw(raw)
        before = self.graph_path.read_bytes()
        r = self.rejected("add-module", "--title", "甲")
        self.assertIn("不合校验", r.err)
        self.assertEqual(self.graph_path.read_bytes(), before)

    def test_deadline_in_case_graph_is_invalid(self):
        self.ok("init", "--full")
        raw = self.read()
        raw["模块"][0]["节点"][0]["时限"] = "偷偷写的"
        self.write_raw(raw)
        r = self.rejected("add-module", "--title", "甲")
        self.assertIn("时限", r.err)

    def test_unknown_format_version_is_refused(self):
        self.write_raw({"格式版本": 99, "领域": "菜园", "模块": []})
        r = self.rejected("add-module", "--title", "甲")
        self.assertIn("格式版本", r.err)

    def test_not_json_is_refused(self):
        self.graph_path.write_text("{oops", encoding="utf-8")
        self.rejected("add-module", "--title", "甲")

    def test_duplicate_title_is_invalid(self):
        self.ok("init", "--full")
        raw = self.read()
        raw["模块"][0]["节点"][1]["标题"] = "松土"
        self.write_raw(raw)
        self.rejected("add-module", "--title", "甲")

    def test_validate_subcommand(self):
        self.ok("init", "--full")
        self.ok("validate")
        self.write_raw({"格式版本": 1})
        self.rejected("validate")

    def test_missing_graph_is_refused(self):
        r = self.rejected("add-module", "--title", "甲")
        self.assertIn("图.json", r.err)


if __name__ == "__main__":
    unittest.main()
