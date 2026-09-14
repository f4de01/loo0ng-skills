"""领域目录三样（AGENTS.md 结构不变量 5，ADR-0004）：assets 下只有领域图、官方模板原件、指引手册原文。

运行：python -m unittest tests/domain/test_assets.py

领域图「破产」由 #30 对两份通用指引手册跑雏形长出：合校验、19 件官方模板每件恰好挂一个节点、
时限句一句话带出处、整份起手后前方为空且每个节点来源为领域图；19 件官方模板与 2 份指引手册按
隐私检查器拆 zip 扫描通过，领域图 JSON 也一并扫；既有案件的 .doc 不进（硬边界 1）。
"""
import functools
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
ASSETS = REPO / "skills" / "in-progress" / "domain" / "assets"
DOMAIN = ASSETS / "破产"
ENGINE = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"
PRIVACY = REPO / "scripts" / "privacy-check.py"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

spec = importlib.util.spec_from_file_location("privacy_check", PRIVACY)
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


@functools.lru_cache(maxsize=1)
def graph() -> dict:
    return json.loads((DOMAIN / "领域图.json").read_text(encoding="utf-8"))


def nodes() -> list:
    return [n for m in graph()["模块"] for n in m["节点"]]


def timed_nodes() -> list:
    return [n for n in nodes() if "时限" in n]


class AssetsTest(unittest.TestCase):
    def test_exactly_three_kinds_and_nothing_else(self):
        self.assertEqual(sorted(p.name for p in ASSETS.iterdir()), ["破产"], "一个领域一个目录")
        self.assertEqual(sorted(p.name for p in DOMAIN.iterdir()), ["指引手册", "模板", "领域图.json"])
        for sub in ("模板", "指引手册"):
            for p in (DOMAIN / sub).iterdir():
                self.assertTrue(p.is_file() and p.suffix == ".docx", "%s 下只放 docx 原件：%s" % (sub, p.name))

    def test_nineteen_templates_and_two_handbooks(self):
        self.assertEqual(len(list((DOMAIN / "模板").glob("*.docx"))), 19)
        self.assertEqual(len(list((DOMAIN / "指引手册").glob("*.docx"))), 2)

    def test_no_legacy_doc_files(self):
        self.assertEqual(list(ASSETS.rglob("*.doc")), [], "既有案件的 .doc 不进领域目录")

    def test_domain_graph_validates(self):
        data = graph()
        self.assertEqual(sorted(data), sorted(["格式版本", "领域", "模块"]))
        self.assertEqual((data["格式版本"], data["领域"]), (1, "破产"))
        self.assertTrue(data["模块"], "领域图不再是空壳（#30）")
        r = subprocess.run([sys.executable, str(ENGINE), "--graph", str(DOMAIN / "领域图.json"), "--kind", "domain", "validate"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_ids_are_stable_readable_and_unique(self):
        seen = set()
        for m in graph()["模块"]:
            for i in [m["id"]] + [n["id"] for n in m["节点"]]:
                self.assertRegex(i, ID_RE, "领域图的 id 由作者给，须是稳定可读的 ASCII")
                self.assertNotIn(i, seen, "id 图内唯一：%s" % i)
                seen.add(i)

    def test_titles_name_one_document_each(self):
        """CONTEXT.md「节点」：每个节点恰有一份文书；实物动作（接管、张贴、签收）不是节点。"""
        文书名 = ("报告", "申请", "申请书", "方案", "通知", "通知书", "公告", "表", "材料", "协议",
                  "规则", "记录", "笔录", "登记册", "计划", "回复", "确认书", "函", "书", "细则")
        for n in nodes():
            head = n["标题"].split("（")[0]  # 括号里只写适用情形，用来分辨同类文书的几件官方模板
            if n["空白模板"] == "无":  # 挂官方模板的节点用官方件自己的名字，那名字就是文书名
                self.assertTrue(head.endswith(文书名), "标题要落在那一份文书上，不能是实物动作：%s" % n["标题"])
            for 同出 in ("并提交", "并报备", "并备案", "并公示", "并移交"):
                self.assertNotIn(同出, head, "一个节点一份文书，同出的两份是两个节点：%s" % n["标题"])
            self.assertNotIn("/", n["标题"], "标题即 文书/<节点标题>/ 的目录名，不能带路径分隔符")

    def test_no_entries_on_a_domain_graph(self):
        for n in nodes():
            self.assertEqual(n["条目"], [], "领域图节点没有条目：%s" % n["标题"])

    def test_every_official_template_is_mounted_on_exactly_one_node(self):
        mounted = []
        for n in nodes():
            tpl = n["空白模板"]
            if tpl == "无":
                continue
            self.assertEqual(tpl["来源"], "官方", "领域图只挂官方模板原件：%s" % n["标题"])
            mounted.append(tpl["文件"])
        on_disk = sorted(p.name for p in (DOMAIN / "模板").glob("*.docx"))
        self.assertEqual(sorted(mounted), on_disk, "19 件官方模板每件恰好挂在一个节点上；同一件不挂两处")

    def test_time_limits_are_one_sentence_with_a_source(self):
        with_limit = timed_nodes()
        self.assertTrue(with_limit, "手册与指引里有天数或锚点的期限要提出来")
        for n in with_limit:
            limit = n["时限"]
            self.assertEqual(limit.splitlines()[:1], [limit], "时限只写一行：%s" % n["标题"])
            出处 = limit.count("（手册") + limit.count("（指引")
            self.assertTrue(出处, "时限句带出处：%s" % n["标题"])
            self.assertLessEqual(出处, 2, "时限只写一句，两个出处括注只留给两源冲突（时限句.md）：%s" % n["标题"])
            self.assertTrue(any(kind in limit for kind in ("法院要求", "法律规定")), "时限句带性质：%s" % n["标题"])

    def test_a_full_init_reads_as_a_workspace_with_nothing_ahead(self):
        """验收（#30）：以整份领域图起手一个测试工作区，前方为空、每个节点标来源领域图、图视图.md 可读。"""
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="domain-30-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        r = subprocess.run([sys.executable, str(ENGINE), "--graph", str(tmp / "图.json"), "--domain", str(DOMAIN),
                            "init", "--full"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        view = json.loads((tmp / "图视图.json").read_text(encoding="utf-8"))
        self.assertEqual(view["前方"], [], "整份起手后前方为空")
        self.assertEqual([m["标题"] for m in view["模块"]], [m["标题"] for m in graph()["模块"]])
        for m in view["模块"]:
            self.assertEqual(m["来源"], "领域图")
            for n in m["节点"]:
                self.assertEqual((n["来源"], n["状态"]), ("领域图", "未生成"))
        md = (tmp / "图视图.md").read_text(encoding="utf-8")
        for m in graph()["模块"]:
            self.assertIn(m["标题"], md)
        limited = timed_nodes()[0]
        self.assertIn(limited["时限"], md, "时限句按 id 从领域图原样带出")

    def test_originals_pass_the_privacy_scan(self):
        for p in sorted(DOMAIN.rglob("*.docx")) + [DOMAIN / "领域图.json"]:
            rel = p.relative_to(REPO).as_posix()
            self.assertEqual(privacy.find_hits_in_line(rel), [], "文件名命中：%s" % rel)
            hits, disclosed = privacy.scan_blob(rel, p.read_bytes())
            self.assertFalse(disclosed, "%s 不是能拆的 Office 文件" % rel)
            self.assertEqual(hits, [], "%s 命中：%s" % (rel, [(h.line, h.category, h.where) for h in hits]))


if __name__ == "__main__":
    unittest.main()
