"""skills/in-progress/filing/scripts/archive.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/filing -p 'test_*.py' -t .

缝是归档 CLI 加工作区里的文件：每个测试用 tests/共用/工作区.py（#12 交付）在临时目录里起一个案件工作区，
写几件合成文件，调 main(argv)，再断文件去了哪、归档索引里多了哪几行、退出码是几。
文件名与内容全是合成的，没有案件内容（ADR-0015）。
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests" / "共用"))
import 工作区 as 工  # noqa: E402

SCRIPT = REPO / "skills" / "in-progress" / "filing" / "scripts" / "archive.py"
spec = importlib.util.spec_from_file_location("loo0ng_archive", SCRIPT)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)

日期 = "2026-09-14"


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class ArchiveCase(unittest.TestCase):
    """一个临时根：下面一格是案件工作区，一格放工作区外的来源目录与计划文件。"""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="filing-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = 工.起工作区(self.tmp / "案件")
        self.根 = self.ws.根
        self._第几份 = 0

    # ------------------------------------------------------------ 造东西

    def 放(self, rel, 内容=b"jia", base=None):
        p = (base or self.ws.待归档) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(内容)
        return p

    def 外部目录(self, 名="外部来源"):
        d = self.tmp / 名
        d.mkdir(parents=True, exist_ok=True)
        return d

    def 计划(self, *条):
        self._第几份 += 1
        p = self.tmp / ("计划%d.json" % self._第几份)
        with open(str(p), "w", encoding="utf-8", newline="\n") as f:
            json.dump(list(条), f, ensure_ascii=False)
        return p

    @staticmethod
    def 条(路径, 去向="材料", 说明="合成件，供测试用", **其他):
        entry = {"路径": 路径, "去向": 去向, "说明": 说明}
        entry.update(其他)
        return entry

    # ------------------------------------------------------------ 调脚本

    def cli(self, *argv, **kw):
        args = ["--workspace", str(kw.get("workspace") or self.根)] + [str(a) for a in argv]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = archive.main(args)
            except SystemExit as e:
                code = e.code
        return Run(code, out.getvalue(), err.getvalue())

    def 搬(self, *条, **kw):
        argv = ["apply", "--plan", self.计划(*条), "--date", kw.get("date", 日期)]
        if kw.get("来源"):
            argv += ["--from", kw["来源"]]
        r = self.cli(*argv)
        self.assertEqual(r.code, 0, r)
        return r

    def 拒(self, *条, **kw):
        argv = ["apply", "--plan", kw.get("plan") or self.计划(*条), "--date", 日期]
        if kw.get("来源"):
            argv += ["--from", kw["来源"]]
        r = self.cli(*argv)
        self.assertEqual(r.code, 1, r)
        self.assertIn("一件都没搬", r.err)
        return r

    # ------------------------------------------------------------ 读回

    def 索引(self):
        p = self.根 / "归档索引.md"
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    def 索引行(self):
        """索引里的数据行，拆成四列。"""
        rows = []
        for line in self.索引().splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 4 and cells[0] not in ("相对路径", "---"):
                rows.append(cells)
        return rows

    def 待归档里的(self):
        return sorted(p.relative_to(self.ws.待归档).as_posix()
                      for p in self.ws.待归档.rglob("*") if p.is_file())


# ---------------------------------------------------------------- list

class ListTest(ArchiveCase):
    def test_empty_pending(self):
        r = self.cli("list")
        self.assertEqual(r.code, 0, r)
        self.assertIn("没有文件", r.out)

    def test_lists_files_with_status(self):
        self.放("合同.pdf", b"contract-body")
        self.放("扫描/照片.jpg", b"photo")
        self.放("已归过的.txt", b"same-bytes")
        self.放("同名的.txt", b"new-bytes")
        (self.ws.材料 / "旧的.txt").write_bytes(b"same-bytes")
        (self.ws.材料 / "同名的.txt").write_bytes(b"old-bytes")
        r = self.cli("list")
        self.assertEqual(r.code, 0, r)
        self.assertIn("合同.pdf\t新", r.out)
        self.assertIn("扫描/照片.jpg\t新", r.out)
        self.assertIn("已归过的.txt\t已有 → 材料/旧的.txt", r.out)
        self.assertIn("同名的.txt\t同名 → 材料/同名的.txt（内容不同）", r.out)
        self.assertIn("共 4 件：新 2，已有 1，同名 1。", r.out)

    def test_lists_outside_directory(self):
        外 = self.外部目录()
        (外 / "函.pdf").write_bytes(b"letter")
        r = self.cli("list", "--from", 外)
        self.assertEqual(r.code, 0, r)
        self.assertIn("函.pdf\t新", r.out)

    def test_not_a_workspace(self):
        别处 = self.tmp / "别处"
        别处.mkdir()
        r = self.cli("list", workspace=别处)
        self.assertEqual(r.code, 1, r)
        self.assertIn("不是案件工作区", r.err)


# ---------------------------------------------------------------- 搬运

class MoveTest(ArchiveCase):
    def test_moves_into_three_destinations(self):
        self.放("合同.pdf", b"contract")
        self.放("空白表.docx", b"blank-form")
        self.放("材料清单.pdf", b"list-bytes")
        r = self.搬(self.条("合同.pdf", "材料", "甲乙买卖合同原件"),
                    self.条("空白表.docx", "参考/模板", "官方空白表"),
                    self.条("材料清单.pdf", "参考/指南", "法院要的材料清单"))
        self.assertTrue((self.ws.材料 / "合同.pdf").is_file())
        self.assertTrue((self.ws.模板 / "空白表.docx").is_file())
        self.assertTrue((self.ws.指南 / "材料清单.pdf").is_file())
        self.assertEqual(self.待归档里的(), [])
        self.assertIn("已归档：合同.pdf → 材料/合同.pdf", r.out)
        self.assertIn("共 3 件：已归档 3，已有 0，同名冲突 0", r.out)

    def test_keeps_subdirectory_path(self):
        self.放("扫描/2026/合同.pdf", b"contract")
        self.搬(self.条("扫描/2026/合同.pdf"))
        self.assertTrue((self.ws.材料 / "扫描" / "2026" / "合同.pdf").is_file())
        self.assertEqual(self.索引行()[0][0], "材料/扫描/2026/合同.pdf")

    def test_prunes_emptied_pending_dirs(self):
        self.放("扫描/合同.pdf", b"contract")
        self.搬(self.条("扫描/合同.pdf"))
        self.assertFalse((self.ws.待归档 / "扫描").exists())
        self.assertTrue(self.ws.待归档.is_dir())

    def test_topic_subdirectory_under_materials(self):
        self.放("合同.pdf", b"contract")
        self.搬(self.条("合同.pdf", "材料", "甲乙买卖合同原件", 子目录="合同类"))
        self.assertTrue((self.ws.材料 / "合同类" / "合同.pdf").is_file())
        self.assertEqual(self.索引行()[0][0], "材料/合同类/合同.pdf")

    def test_topic_subdirectory_only_under_materials(self):
        self.放("空白表.docx", b"blank-form")
        r = self.拒(self.条("空白表.docx", "参考/模板", "官方空白表", 子目录="表格"))
        self.assertIn("只有 材料 下能建主题子目录", r.err)
        self.assertEqual(self.待归档里的(), ["空白表.docx"])

    def test_never_renames_or_overwrites(self):
        (self.ws.材料 / "合同.pdf").write_bytes(b"first-bytes")
        self.放("合同.pdf", b"second-bytes")
        r = self.搬(self.条("合同.pdf"))
        self.assertIn("同名冲突：合同.pdf → 材料/合同.pdf 已存在且内容不同，未搬", r.out)
        self.assertEqual((self.ws.材料 / "合同.pdf").read_bytes(), b"first-bytes")
        self.assertEqual(self.待归档里的(), ["合同.pdf"])
        self.assertEqual(self.索引行(), [])
        self.assertEqual(sorted(p.name for p in self.ws.材料.iterdir()), ["合同.pdf"])

    def test_same_content_reported_as_already_there(self):
        (self.ws.指南 / "通知.pdf").write_bytes(b"same-bytes")
        self.放("又一份通知.pdf", b"same-bytes")
        r = self.搬(self.条("又一份通知.pdf", "材料", "看着像通知"))
        self.assertIn("已有：又一份通知.pdf（与 参考/指南/通知.pdf 内容相同，未搬）", r.out)
        self.assertEqual(self.待归档里的(), ["又一份通知.pdf"])
        self.assertEqual(self.索引行(), [])

    def test_same_content_twice_in_one_plan(self):
        self.放("甲.txt", b"same-bytes")
        self.放("乙.txt", b"same-bytes")
        r = self.搬(self.条("甲.txt"), self.条("乙.txt"))
        self.assertIn("已归档：甲.txt → 材料/甲.txt", r.out)
        self.assertIn("已有：乙.txt（与 材料/甲.txt 内容相同，未搬）", r.out)
        self.assertEqual(self.待归档里的(), ["乙.txt"])
        self.assertEqual(len(self.索引行()), 1)

    def test_partial_outcomes_still_exit_zero(self):
        (self.ws.材料 / "甲.txt").write_bytes(b"first-bytes")
        self.放("甲.txt", b"second-bytes")
        self.放("乙.txt", b"new-bytes")
        r = self.搬(self.条("甲.txt"), self.条("乙.txt"))
        self.assertEqual(r.code, 0, r)
        self.assertIn("共 2 件：已归档 1，已有 0，同名冲突 1", r.out)
        self.assertTrue((self.ws.材料 / "乙.txt").is_file())


# ---------------------------------------------------------------- 工作区外

class OutsideTest(ArchiveCase):
    def test_copies_and_leaves_original(self):
        外 = self.外部目录()
        (外 / "函.pdf").write_bytes(b"letter")
        r = self.搬(self.条("函.pdf", "材料", "对方发来的函"), 来源=外)
        self.assertTrue((外 / "函.pdf").is_file())
        self.assertEqual((self.ws.材料 / "函.pdf").read_bytes(), b"letter")
        self.assertIn("（复制，原件不动）", r.out)
        self.assertEqual(self.索引行()[0][0], "材料/函.pdf")

    def test_copy_twice_is_already_there(self):
        外 = self.外部目录()
        (外 / "函.pdf").write_bytes(b"letter")
        self.搬(self.条("函.pdf"), 来源=外)
        r = self.搬(self.条("函.pdf"), 来源=外)
        self.assertIn("已有：函.pdf（与 材料/函.pdf 内容相同，未搬）", r.out)
        self.assertEqual(len(self.索引行()), 1)

    def test_source_inside_workspace_refused(self):
        self.放("合同.pdf", b"contract")
        r = self.拒(self.条("合同.pdf"), 来源=self.ws.待归档)
        self.assertIn("在本案工作区里", r.err)
        self.assertEqual(self.待归档里的(), ["合同.pdf"])

    def test_source_wrapping_workspace_refused(self):
        r = self.拒(self.条("随便.pdf"), 来源=self.tmp)
        self.assertIn("套着本案工作区", r.err)

    def test_source_not_a_directory(self):
        文件 = self.tmp / "不是目录.txt"
        文件.write_bytes(b"x")
        r = self.拒(self.条("随便.pdf"), 来源=文件)
        self.assertIn("不是一个目录", r.err)


# ---------------------------------------------------------------- 整条拒绝

class RefuseTest(ArchiveCase):
    def test_absolute_path(self):
        self.放("合同.pdf")
        r = self.拒(self.条(str(self.ws.待归档 / "合同.pdf")))
        self.assertIn("是绝对路径", r.err)
        self.assertEqual(self.待归档里的(), ["合同.pdf"])

    def test_dot_dot_escapes(self):
        self.放("合同.pdf")
        r = self.拒(self.条("../图.json"))
        self.assertIn("越界", r.err)
        self.assertEqual(self.待归档里的(), ["合同.pdf"])

    def test_one_bad_entry_moves_nothing(self):
        self.放("合同.pdf")
        self.放("通知.pdf")
        r = self.拒(self.条("合同.pdf"), self.条("通知.pdf", "参考/其他"))
        self.assertIn("不是三格之一", r.err)
        self.assertEqual(self.待归档里的(), ["合同.pdf", "通知.pdf"])
        self.assertEqual(self.索引(), "")

    def test_missing_file(self):
        r = self.拒(self.条("没有这件.pdf"))
        self.assertIn("没有 没有这件.pdf", r.err)

    def test_directory_entry(self):
        self.放("扫描/合同.pdf")
        r = self.拒(self.条("扫描"))
        self.assertIn("是目录", r.err)
        self.assertEqual(self.待归档里的(), ["扫描/合同.pdf"])

    def test_missing_required_field(self):
        self.放("合同.pdf")
        r = self.拒({"路径": "合同.pdf", "去向": "材料"})
        self.assertIn("缺 说明", r.err)

    def test_note_with_pipe(self):
        self.放("合同.pdf")
        r = self.拒(self.条("合同.pdf", "材料", "甲 | 乙"))
        self.assertIn("不得含竖线", r.err)

    def test_unknown_field(self):
        self.放("合同.pdf")
        r = self.拒(self.条("合同.pdf", 性质="直接陈述"))
        self.assertIn("不认得的字段", r.err)

    def test_same_path_twice(self):
        self.放("合同.pdf")
        r = self.拒(self.条("合同.pdf"), self.条("合同.pdf", "参考/指南"))
        self.assertIn("给了两次", r.err)

    def test_two_entries_one_target(self):
        self.放("甲/合同.pdf", b"jia-bytes")
        self.放("卷一/甲/合同.pdf", b"yi-bytes")
        r = self.拒(self.条("甲/合同.pdf", "材料", "加了主题子目录的那份", 子目录="卷一"),
                    self.条("卷一/甲/合同.pdf", "材料", "原样保子目录的那份"))
        self.assertIn("两条都落到", r.err)

    def test_never_writes_lawyer_sayings(self):
        (self.ws.材料 / "律师说过的.md").write_text("原有一行\n", encoding="utf-8")
        self.放("律师说过的.md", b"fake-bytes")
        r = self.拒(self.条("律师说过的.md"))
        self.assertIn("归档永不写它", r.err)
        self.assertEqual((self.ws.材料 / "律师说过的.md").read_text(encoding="utf-8"), "原有一行\n")

    def test_bad_plan_file(self):
        r = self.cli("apply", "--plan", self.tmp / "没有这份.json")
        self.assertEqual(r.code, 1, r)
        self.assertIn("读不到计划", r.err)

    def test_plan_not_an_array(self):
        p = self.tmp / "计划.json"
        p.write_text('{"路径": "合同.pdf"}', encoding="utf-8")
        r = self.cli("apply", "--plan", p)
        self.assertEqual(r.code, 1, r)
        self.assertIn("非空 JSON 数组", r.err)

    def test_usage_error_is_two(self):
        self.assertEqual(self.cli().code, 2)
        self.assertEqual(self.cli("apply").code, 2)
        self.assertEqual(self.cli("list", "--to", "材料").code, 2)

    def test_bad_date(self):
        self.放("合同.pdf")
        r = self.cli("apply", "--plan", self.计划(self.条("合同.pdf")), "--date", "2026年9月14日")
        self.assertEqual(r.code, 1, r)
        self.assertIn("YYYY-MM-DD", r.err)


# ---------------------------------------------------------------- 归档索引

class IndexTest(ArchiveCase):
    def test_one_row_per_file(self):
        self.放("合同.pdf", b"contract")
        self.放("通知.pdf", b"notice")
        self.搬(self.条("合同.pdf", "材料", "甲乙买卖合同原件"),
                self.条("通知.pdf", "参考/指南", "法院的受理通知"))
        self.assertEqual(self.索引行(), [
            ["材料/合同.pdf", "甲乙买卖合同原件", 日期, "原件"],
            ["参考/指南/通知.pdf", "法院的受理通知", 日期, "原件"],
        ])

    def test_appends_without_reordering(self):
        self.放("甲.txt", b"jia")
        self.搬(self.条("甲.txt", "材料", "第一件"))
        self.放("乙.txt", b"yi")
        self.搬(self.条("乙.txt", "材料", "第二件"))
        self.assertEqual([r[0] for r in self.索引行()], ["材料/甲.txt", "材料/乙.txt"])
        self.assertIn("# 归档索引", self.索引())

    def test_updates_existing_row_in_place(self):
        self.放("甲.txt", b"jia")
        self.放("乙.txt", b"yi")
        self.搬(self.条("甲.txt", "材料", "第一件"), self.条("乙.txt", "材料", "第二件"))
        (self.ws.材料 / "甲.txt").unlink()            # 律师自己删掉了那一件
        self.放("甲.txt", b"jia-again")
        self.搬(self.条("甲.txt", "材料", "重新拿到的第一件"), date="2026-09-20")
        self.assertEqual(self.索引行(), [
            ["材料/甲.txt", "重新拿到的第一件", "2026-09-20", "原件"],
            ["材料/乙.txt", "第二件", 日期, "原件"],
        ])

    def test_keeps_unknown_lines(self):
        self.放("甲.txt", b"jia")
        self.搬(self.条("甲.txt", "材料", "第一件"))
        路径 = self.根 / "归档索引.md"
        路径.write_text(self.索引() + "\n手写的一段，脚本不该动它。\n", encoding="utf-8")
        self.放("乙.txt", b"yi")
        self.搬(self.条("乙.txt", "材料", "第二件"))
        self.assertIn("手写的一段，脚本不该动它。", self.索引())
        self.assertEqual([r[0] for r in self.索引行()], ["材料/甲.txt", "材料/乙.txt"])

    def test_default_date_is_today(self):
        import datetime
        self.放("甲.txt", b"jia")
        r = self.cli("apply", "--plan", self.计划(self.条("甲.txt")))
        self.assertEqual(r.code, 0, r)
        self.assertEqual(self.索引行()[0][2], datetime.date.today().isoformat())


# ---------------------------------------------------------------- 不碰图

class GraphUntouchedTest(ArchiveCase):
    def test_graph_and_views_untouched(self):
        before = [p.read_bytes() for p in (self.ws.图, self.ws.视图md, self.ws.视图json)]
        self.放("合同.pdf", b"contract")
        self.搬(self.条("合同.pdf"))
        self.拒(self.条("../图.json"))
        after = [p.read_bytes() for p in (self.ws.图, self.ws.视图md, self.ws.视图json)]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
