"""出厂预设图三样（AGENTS.md 结构不变量 5，ADR-0023）：assets/预设图/<名>/ 下只有预设图、模板原件、指引手册原文。

运行：python -m unittest tests/domain/test_assets.py

出厂那份「破产」由 #30 对两份通用指引手册长出、#16 随预设图改形：合校验（格式版本 2、无「领域」
字段、空白模板只记文件名）、19 件官方模板每件恰好挂一个节点、时限句一句话带出处、整份起手后
12 个模块 72 个节点都在前方；包内的出厂件谁都不许写，引擎无条件拒。19 件官方模板与 2 份指引手册
按隐私检查器拆 zip 扫描通过，预设图 JSON 也一并扫；既有案件的 .doc 不进（硬边界 1）。
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
PRESETS = ASSETS / "预设图"
破产 = PRESETS / "破产"
图文件 = 破产 / "预设图.json"
ENGINE = REPO / "skills" / "in-progress" / "graph" / "scripts" / "graph.py"
PRIVACY = REPO / "scripts" / "privacy-check.py"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

spec = importlib.util.spec_from_file_location("privacy_check", PRIVACY)
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


def 引擎(*argv):
    return subprocess.run([sys.executable, str(ENGINE), *map(str, argv)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


@functools.lru_cache(maxsize=1)
def graph() -> dict:
    return json.loads(图文件.read_text(encoding="utf-8"))


def nodes() -> list:
    return [n for m in graph()["模块"] for n in m["节点"]]


def timed_nodes() -> list:
    return [n for n in nodes() if "时限" in n]


class 形状(unittest.TestCase):
    def test_assets_下只有预设图那一格(self):
        self.assertEqual(sorted(p.name for p in ASSETS.iterdir()), ["预设图"])

    def test_一份预设图三样别的不放(self):
        for d in sorted(PRESETS.iterdir()):
            self.assertTrue(d.is_dir(), "预设图/ 下一个名字一个目录：%s" % d.name)
            self.assertEqual(sorted(p.name for p in d.iterdir()), ["指引手册", "模板", "预设图.json"])
            for sub in ("模板", "指引手册"):
                for p in (d / sub).iterdir():
                    self.assertTrue(p.is_file() and p.suffix == ".docx", "%s 下只放 docx 原件：%s" % (sub, p.name))

    def test_十九件模板两份手册(self):
        self.assertEqual(len(list((破产 / "模板").glob("*.docx"))), 19)
        self.assertEqual(len(list((破产 / "指引手册").glob("*.docx"))), 2)

    def test_既有案件的doc不进(self):
        self.assertEqual(list(ASSETS.rglob("*.doc")), [], "既有案件的 .doc 不进出厂预设图")


class 图本身(unittest.TestCase):
    def test_合预设图的校验(self):
        data = graph()
        self.assertEqual(set(data), {"格式版本", "模块"}, "顶层不带「领域」（ADR-0023）")
        self.assertEqual(data["格式版本"], 2)
        self.assertEqual((len(data["模块"]), len(nodes())), (12, 72))
        r = 引擎("--graph", 图文件, "--kind", "preset", "validate")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_id稳定可读且唯一(self):
        seen = set()
        for m in graph()["模块"]:
            for i in [m["id"]] + [n["id"] for n in m["节点"]]:
                self.assertRegex(i, ID_RE, "预设图的 id 由作者给，须是稳定可读的 ASCII")
                self.assertNotIn(i, seen, "id 图内唯一：%s" % i)
                seen.add(i)

    def test_没有条目(self):
        for n in nodes():
            self.assertEqual(n["条目"], [], "预设图节点没有条目：%s" % n["标题"])

    def test_标题落在一份文书上(self):
        """CONTEXT.md「节点」：每个节点恰有一份文书；实物动作（接管、张贴、签收）不是节点。"""
        文书名 = ("报告", "申请", "申请书", "方案", "通知", "通知书", "公告", "表", "材料", "协议",
                  "规则", "记录", "笔录", "登记册", "计划", "回复", "确认书", "函", "书", "细则")
        for n in nodes():
            head = n["标题"].split("（")[0]  # 括号里只写适用情形，用来分辨同类文书的几件官方模板
            if n["空白模板"] == "无":  # 挂官方模板的节点用官方件自己的名字，那名字就是文书名
                self.assertTrue(head.endswith(文书名), "标题要落在那一份文书上，不能是实物动作：%s" % n["标题"])
            for 同出 in ("并提交", "并报备", "并备案", "并公示", "并移交"):
                self.assertNotIn(同出, head, "一个节点一份文书，同出的两份是两个节点：%s" % n["标题"])
            self.assertNotIn("/", n["标题"], "标题即文书目录名，不能带路径分隔符")

    def test_每件官方模板恰好挂一个节点(self):
        mounted = []
        for n in nodes():
            tpl = n["空白模板"]
            if tpl == "无":
                continue
            self.assertIsInstance(tpl, str, "空白模板只记文件名（ADR-0023）：%s" % n["标题"])
            self.assertNotIn(":", tpl, "不再有「来源:文件」的旧写法：%s" % n["标题"])
            mounted.append(tpl)
        on_disk = sorted(p.name for p in (破产 / "模板").glob("*.docx"))
        self.assertEqual(sorted(mounted), on_disk, "19 件官方模板每件恰好挂在一个节点上；同一件不挂两处")

    def test_时限一句话带出处(self):
        with_limit = timed_nodes()
        self.assertTrue(with_limit, "手册与指引里有天数或锚点的期限要提出来")
        for n in with_limit:
            limit = n["时限"]
            self.assertEqual(limit.splitlines()[:1], [limit], "时限只写一行：%s" % n["标题"])
            出处 = limit.count("（手册") + limit.count("（指引")
            self.assertTrue(出处, "时限句带出处：%s" % n["标题"])
            self.assertLessEqual(出处, 2, "时限只写一句，两个出处括注只留给两源冲突（时限句.md）：%s" % n["标题"])
            self.assertTrue(any(kind in limit for kind in ("法院要求", "法律规定")), "时限句带性质：%s" % n["标题"])


class 拿它起手(unittest.TestCase):
    def test_整份拷入后十二个模块都在前方(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="preset-30-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        r = 引擎("--graph", tmp / "图.json", "init", "--preset", 破产)
        self.assertEqual(r.returncode, 0, r.stderr)
        view = json.loads((tmp / "图视图.json").read_text(encoding="utf-8"))
        self.assertEqual([m["标题"] for m in view["模块"]], [m["标题"] for m in graph()["模块"]])
        前方节点 = [n["标题"] for m in view["前方"] for n in m["节点"]]
        self.assertEqual(len(前方节点), 72, "起手之后一个节点都没生成，全在前方（案件图自足，ADR-0023）")
        for m in view["模块"]:
            for n in m["节点"]:
                self.assertEqual(n["状态"], "未生成")
        md = (tmp / "图视图.md").read_text(encoding="utf-8")
        for m in graph()["模块"]:
            self.assertIn(m["标题"], md)
        self.assertIn(timed_nodes()[0]["时限"], md, "时限句随起手整份拷进案件图，视图原样带出")


class 拒写(unittest.TestCase):
    def test_包内出厂件谁都不许写(self):
        before = 图文件.read_bytes()
        r = 引擎("--graph", 图文件, "--kind", "preset", "add-module", "--title", "试着写一笔", "--id", "m-test")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("出厂", r.stderr)
        self.assertEqual(图文件.read_bytes(), before, "拒了就一字不动")

    def test_只读的用法一条不碎(self):
        self.assertEqual(引擎("--graph", 图文件, "--kind", "preset", "validate").returncode, 0)


class 隐私(unittest.TestCase):
    def test_原件过隐私扫描(self):
        for p in sorted(破产.rglob("*.docx")) + [图文件]:
            rel = p.relative_to(REPO).as_posix()
            self.assertEqual(privacy.find_hits_in_line(rel), [], "文件名命中：%s" % rel)
            hits, disclosed = privacy.scan_blob(rel, p.read_bytes())
            self.assertFalse(disclosed, "%s 不是能拆的 Office 文件" % rel)
            self.assertEqual(hits, [], "%s 命中：%s" % (rel, [(h.line, h.category, h.where) for h in hits]))

    def test_预设图那份图在main上被守着(self):
        rel = 图文件.relative_to(REPO).as_posix()
        self.assertTrue(privacy.is_guarded_path(rel), "隐私钩子守的路径前缀要跟着预设图改（ADR-0023）")
        self.assertFalse(privacy.is_guarded_path((破产 / "模板" / "某件.docx").relative_to(REPO).as_posix()),
                         "同目录的模板原件按定义不含案件内容，不守")


if __name__ == "__main__":
    unittest.main()
