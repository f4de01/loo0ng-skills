"""skills/engineering/filing/scripts/statement.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/filing/test_statement.py

缝是落档 CLI 加工作区里的 材料/律师陈述/：每个测试在临时工作区里建 图.json，调 main(argv)，再读落下的文件断言。
原话与标题全是合成的（菜园领域），没有案件内容（ADR-0015）。
"""
import contextlib
import importlib.util
import io
import os
import pathlib
import re
import shutil
import stat
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "engineering" / "filing" / "scripts" / "statement.py"

spec = importlib.util.spec_from_file_location("loo0ng_statement", SCRIPT)
statement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(statement)

AT = "2026-09-06T10:20:30+08:00"
FILENAME_RE = re.compile(r"^\d{8}-\d{6}-[^\s.]{1,20}\.md$")
FIELDS = ["性质", "转述来源", "录入时间", "节点", "回应", "取代"]


def split(text):
    """按 ADR-0013 的读法：front matter 按行切 键: 值，返回 (有序键列表, 字典, 正文)。"""
    assert text.startswith("---\n"), "文件须以 --- 起头"
    head, _, body = text[4:].partition("\n---\n")
    keys, data = [], {}
    for line in head.splitlines():
        k, sep, v = line.partition(":")
        assert sep, "头部行不是 键: 值：%r" % line
        keys.append(k)
        data[k] = v.strip()
    return keys, data, body


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class StatementCase(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp(prefix="filing-test-"))
        self.addCleanup(self._cleanup)
        (self.ws / "图.json").write_text("{}", encoding="utf-8")
        self.dir = self.ws / "材料" / "律师陈述"

    def _cleanup(self):
        for p in self.ws.rglob("*"):
            if p.is_file():
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        shutil.rmtree(self.ws, True)

    def cli(self, *argv, workspace=None, at=AT):
        args = ["--workspace", str(workspace or self.ws)]
        if at:
            args += ["--at", at]
        args += list(argv)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = statement.main(args)
            except SystemExit as e:
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

    def files(self):
        return sorted(p.name for p in self.dir.iterdir()) if self.dir.is_dir() else []

    def only_file(self):
        names = self.files()
        self.assertEqual(len(names), 1, names)
        return self.dir / names[0]

    def read_only_file(self):
        return split(self.only_file().read_text(encoding="utf-8"))


class WriteTest(StatementCase):
    def test_filename_and_six_fields_in_order(self):
        r = self.ok("--nature", "直接陈述", "--title", "东头地块去年种番茄", "--words", "东头那块地去年种的是番茄。")
        path = self.only_file()
        self.assertEqual(path.name, "20260906-102030-东头地块去年种番茄.md")
        self.assertRegex(path.name, FILENAME_RE)
        keys, data, body = split(path.read_text(encoding="utf-8"))
        self.assertEqual(keys, FIELDS)
        self.assertEqual(data["性质"], "直接陈述")
        self.assertEqual(data["转述来源"], "")
        self.assertEqual(data["录入时间"], AT)
        self.assertEqual(data["节点"], "")
        self.assertEqual(data["回应"], "")
        self.assertEqual(data["取代"], "")
        self.assertIn("已落档：材料/律师陈述/20260906-102030-东头地块去年种番茄.md", r.out)

    def test_verbatim_words_and_no_summary_for_single_value(self):
        words = "东头那块地去年种的是番茄，  今年别再种了。"
        self.ok("--nature", "直接陈述", "--title", "东头轮作", "--words", words)
        _, _, body = self.read_only_file()
        self.assertIn("## 原话\n\n%s\n" % words, body)
        self.assertNotIn("## 整理", body)
        self.assertNotIn("## 问题", body)

    def test_multi_value_summary_table_marked_as_agent(self):
        self.ok("--nature", "直接陈述", "--title", "地块与面积", "--words", "东头三分地，西头两分。",
                "--item", "东头=三分", "--item", "西头=两分")
        _, _, body = self.read_only_file()
        self.assertIn("## 原话", body)
        self.assertIn("## 整理", body)
        self.assertIn("agent 整理", body)
        self.assertIn("| 项目 | 值 |", body)
        self.assertIn("| 东头 | 三分 |", body)
        self.assertIn("| 西头 | 两分 |", body)
        self.assertLess(body.index("## 原话"), body.index("## 整理"))

    def test_item_needs_equals(self):
        self.rejected("--nature", "直接陈述", "--title", "地块", "--words", "x", "--item", "东头三分")
        self.assertEqual(self.files(), [])

    def test_nodes_reply_and_source(self):
        self.ok("--nature", "转述", "--source", "邻居老张", "--title", "邻居说地力", "--words", "老张说那块地肥。",
                "--node", "松土", "--node", "施底肥", "--reply", "文书/松土/松土-v1-审查报告.md")
        _, data, _ = self.read_only_file()
        self.assertEqual(data["性质"], "转述")
        self.assertEqual(data["转述来源"], "邻居老张")
        self.assertEqual(data["节点"], "松土；施底肥")
        self.assertEqual(data["回应"], "文书/松土/松土-v1-审查报告.md")

    def test_relay_requires_source(self):
        r = self.rejected("--nature", "转述", "--title", "邻居说地力", "--words", "老张说那块地肥。")
        self.assertIn("转述来源", r.err)
        self.assertEqual(self.files(), [])

    def test_source_only_for_relay(self):
        r = self.rejected("--nature", "直接陈述", "--source", "老张", "--title", "地力", "--words", "肥。")
        self.assertIn("转述", r.err)
        self.assertEqual(self.files(), [])

    def test_ruling_has_fixed_two_sections(self):
        self.ok("--nature", "裁定", "--title", "先种番茄", "--question", "东头先种番茄还是黄瓜？",
                "--words", "先种番茄。")
        _, data, body = self.read_only_file()
        self.assertEqual(data["性质"], "裁定")
        self.assertIn("## 问题\n\n东头先种番茄还是黄瓜？\n", body)
        self.assertIn("## 裁定\n\n先种番茄。\n", body)
        self.assertNotIn("## 原话", body)
        self.assertNotIn("## 整理", body)
        self.assertLess(body.index("## 问题"), body.index("## 裁定"))

    def test_ruling_requires_question_and_refuses_items(self):
        r = self.rejected("--nature", "裁定", "--title", "先种番茄", "--words", "先种番茄。")
        self.assertIn("问题", r.err)
        self.rejected("--nature", "裁定", "--title", "先种番茄", "--question", "先种啥？", "--words", "番茄。",
                      "--item", "东头=番茄")
        self.assertEqual(self.files(), [])

    def test_question_only_for_ruling(self):
        self.rejected("--nature", "直接陈述", "--title", "地力", "--question", "肥吗？", "--words", "肥。")
        self.assertEqual(self.files(), [])

    def test_supersedes_existing_file_in_same_dir(self):
        self.ok("--nature", "直接陈述", "--title", "东头种番茄", "--words", "东头种番茄。", at="2026-09-06T10:00:00+08:00")
        old = self.files()[0]
        r = self.ok("--nature", "直接陈述", "--title", "东头改种黄瓜", "--words", "东头改种黄瓜。",
                    "--supersedes", old)
        names = self.files()
        self.assertEqual(len(names), 2)
        new = self.dir / "20260906-102030-东头改种黄瓜.md"
        _, data, _ = split(new.read_text(encoding="utf-8"))
        self.assertEqual(data["取代"], old)
        self.assertIn(old, r.out)
        old_text = (self.dir / old).read_text(encoding="utf-8")
        self.assertNotIn("取代: 2", old_text, "旧文件一字不动")

    def test_supersedes_missing_target_is_rejected(self):
        r = self.rejected("--nature", "直接陈述", "--title", "东头改种黄瓜", "--words", "改。",
                          "--supersedes", "20260101-000000-不存在.md")
        self.assertIn("取代", r.err)
        self.assertEqual(self.files(), [])

    def test_supersedes_must_be_bare_filename(self):
        self.ok("--nature", "直接陈述", "--title", "旧", "--words", "旧。", at="2026-09-06T10:00:00+08:00")
        old = self.files()[0]
        self.rejected("--nature", "直接陈述", "--title", "新", "--words", "新。", "--supersedes", "材料/律师陈述/" + old)
        self.rejected("--nature", "直接陈述", "--title", "新", "--words", "新。", "--supersedes", "../" + old)
        self.assertEqual(len(self.files()), 1)

    def test_refuses_overwrite(self):
        self.ok("--nature", "直接陈述", "--title", "同题", "--words", "一。")
        r = self.rejected("--nature", "直接陈述", "--title", "同题", "--words", "二。")
        self.assertIn("已存在", r.err)
        _, _, body = self.read_only_file()
        self.assertIn("一。", body)
        self.assertNotIn("二。", body)

    def test_written_file_is_read_only(self):
        self.ok("--nature", "直接陈述", "--title", "只读", "--words", "只读。")
        path = self.only_file()
        self.assertFalse(os.access(path, os.W_OK), "落盘后应只读")
        with self.assertRaises(PermissionError):
            path.write_text("改", encoding="utf-8")

    def test_title_rules(self):
        base = ["--nature", "直接陈述", "--words", "x"]
        self.rejected(*base, "--title", "")
        self.rejected(*base, "--title", "二十一个字二十一个字二十一个字二十一个字二")
        self.rejected(*base, "--title", "有，标点")
        self.rejected(*base, "--title", "有 空格")
        self.rejected(*base, "--title", "带/斜杠")
        self.rejected(*base, "--title", "带.点")
        self.assertEqual(self.files(), [])
        self.ok(*base, "--title", "二十个字二十个字二十个字二十个字二十")
        self.ok(*base, "--title", "地块2号A", at="2026-09-06T10:00:01+08:00")

    def test_single_line_header_values(self):
        self.rejected("--nature", "转述", "--source", "老张\n老李", "--title", "来源", "--words", "x")
        self.rejected("--nature", "直接陈述", "--node", "松土\n施底肥", "--title", "节点", "--words", "x")
        self.assertEqual(self.files(), [])

    def test_empty_words_rejected(self):
        self.rejected("--nature", "直接陈述", "--title", "空话", "--words", "   ")
        self.assertEqual(self.files(), [])

    def test_bad_nature_is_usage_error(self):
        r = self.cli("--nature", "备注", "--title", "x", "--words", "x")
        self.assertEqual(r.code, 2, r)

    def test_requires_workspace_marker(self):
        other = pathlib.Path(tempfile.mkdtemp(prefix="filing-nows-"))
        self.addCleanup(shutil.rmtree, other, True)
        r = self.rejected("--nature", "直接陈述", "--title", "x", "--words", "x", workspace=other)
        self.assertIn("图.json", r.err)
        self.assertFalse((other / "材料").exists())

    def test_default_time_is_now(self):
        self.ok("--nature", "直接陈述", "--title", "此刻", "--words", "现在。", at=None)
        path = self.only_file()
        self.assertRegex(path.name, FILENAME_RE)
        _, data, _ = split(path.read_text(encoding="utf-8"))
        self.assertRegex(data["录入时间"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
        self.assertEqual(path.name[:15], data["录入时间"][:10].replace("-", "") + "-" + data["录入时间"][11:19].replace(":", ""))

    def test_no_bom_and_lf(self):
        self.ok("--nature", "直接陈述", "--title", "编码", "--words", "两行\n原话")
        raw = self.only_file().read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertIn("两行\n原话".encode("utf-8"), raw)

    def test_does_not_touch_graph_or_other_dirs(self):
        self.ok("--nature", "直接陈述", "--title", "只写陈述", "--words", "x")
        self.assertEqual((self.ws / "图.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual(sorted(p.name for p in self.ws.iterdir()), ["图.json", "材料"])
        self.assertEqual(sorted(p.name for p in (self.ws / "材料").iterdir()), ["律师陈述"])


if __name__ == "__main__":
    unittest.main()
