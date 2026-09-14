"""skills/in-progress/filing/scripts/archive.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/filing/test_archive.py

缝是归档 CLI 加工作区里的文件：每个测试在临时工作区里建 图.json 与 收件箱/，调 main(argv)，再看文件去了哪。
文件名与内容全是合成的，没有案件内容（ADR-0015）。
"""
import contextlib
import importlib.util
import io
import pathlib
import shutil
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills" / "in-progress" / "filing" / "scripts" / "archive.py"

spec = importlib.util.spec_from_file_location("loo0ng_archive", SCRIPT)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class Run:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return "Run(code=%r, out=%r, err=%r)" % (self.code, self.out, self.err)


class ArchiveCase(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp(prefix="filing-test-"))
        self.addCleanup(shutil.rmtree, self.ws, True)
        (self.ws / "图.json").write_text("{}", encoding="utf-8")
        self.inbox = self.ws / "收件箱"
        self.inbox.mkdir()

    def put(self, rel, content=b"x"):
        p = self.inbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return p

    def cli(self, *argv, workspace=None):
        args = ["--workspace", str(workspace or self.ws)] + list(argv)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = archive.main(args)
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

    def inbox_files(self):
        return sorted(p.relative_to(self.inbox).as_posix() for p in self.inbox.rglob("*") if p.is_file())


class MoveTest(ArchiveCase):
    def test_moves_file_to_each_destination_without_renaming(self):
        for dest in ("材料", "指南", "模板/官方", "模板/生成"):
            name = "文件-%s.txt" % dest.replace("/", "-")
            self.put(name, b"abc")
            r = self.ok("move", "--to", dest, name)
            target = self.ws / dest / name
            self.assertTrue(target.is_file(), r)
            self.assertEqual(target.read_bytes(), b"abc")
            self.assertFalse((self.inbox / name).exists())
            self.assertIn("%s/%s" % (dest, name), r.out)

    def test_keeps_subdirectory_relative_path(self):
        self.put("甲方/2025/清单.xlsx", b"1")
        self.ok("move", "--to", "材料", "甲方/2025/清单.xlsx")
        self.assertTrue((self.ws / "材料" / "甲方" / "2025" / "清单.xlsx").is_file())
        self.assertFalse((self.inbox / "甲方").exists(), "搬空后的收件箱子目录应清掉")
        self.assertTrue(self.inbox.is_dir(), "收件箱本身要留着")

    def test_prunes_only_emptied_dirs(self):
        self.put("甲方/a.txt")
        self.put("甲方/b.txt")
        self.ok("move", "--to", "材料", "甲方/a.txt")
        self.assertEqual(self.inbox_files(), ["甲方/b.txt"])

    def test_moves_whole_directory(self):
        self.put("乙方/x.txt", b"x")
        self.put("乙方/深/y.txt", b"y")
        self.ok("move", "--to", "指南", "乙方")
        self.assertEqual((self.ws / "指南" / "乙方" / "深" / "y.txt").read_bytes(), b"y")
        self.assertEqual(self.inbox_files(), [])

    def test_backslash_relative_path_is_accepted(self):
        self.put("甲方/清单.txt")
        self.ok("move", "--to", "材料", "甲方\\清单.txt")
        self.assertTrue((self.ws / "材料" / "甲方" / "清单.txt").is_file())

    def test_same_name_exists_is_not_moved_and_reported(self):
        self.put("同名.pdf", b"new")
        (self.ws / "材料").mkdir()
        (self.ws / "材料" / "同名.pdf").write_bytes(b"old")
        r = self.rejected("move", "--to", "材料", "同名.pdf")
        self.assertEqual((self.ws / "材料" / "同名.pdf").read_bytes(), b"old", "不得覆盖")
        self.assertEqual(self.inbox_files(), ["同名.pdf"], "同名件留在收件箱")
        self.assertIn("同名.pdf", r.out)
        self.assertIn("已存在", r.out)

    def test_same_name_directory_is_not_merged(self):
        self.put("丙方/新.txt")
        (self.ws / "材料" / "丙方").mkdir(parents=True)
        (self.ws / "材料" / "丙方" / "旧.txt").write_bytes(b"old")
        self.rejected("move", "--to", "材料", "丙方")
        self.assertEqual(self.inbox_files(), ["丙方/新.txt"])
        self.assertFalse((self.ws / "材料" / "丙方" / "新.txt").exists())

    def test_batch_moves_others_when_one_collides(self):
        self.put("a.txt")
        self.put("b.txt")
        (self.ws / "材料").mkdir()
        (self.ws / "材料" / "a.txt").write_bytes(b"old")
        r = self.rejected("move", "--to", "材料", "a.txt", "b.txt")
        self.assertTrue((self.ws / "材料" / "b.txt").is_file(), r)
        self.assertEqual(self.inbox_files(), ["a.txt"])

    def test_rejects_parent_traversal_and_moves_nothing(self):
        outside = self.ws / "外面.txt"
        outside.write_bytes(b"o")
        self.put("正常.txt")
        r = self.rejected("move", "--to", "材料", "../外面.txt", "正常.txt")
        self.assertTrue(outside.is_file())
        self.assertEqual(self.inbox_files(), ["正常.txt"], "越界时整条命令不搬")
        self.assertIn("越界", r.err)

    def test_rejects_dotdot_in_middle(self):
        self.put("甲方/a.txt")
        (self.ws / "外面.txt").write_bytes(b"o")
        self.rejected("move", "--to", "材料", "甲方/../../外面.txt")
        self.assertTrue((self.ws / "外面.txt").is_file())

    def test_rejects_absolute_path(self):
        p = self.put("绝对.txt")
        r = self.rejected("move", "--to", "材料", str(p))
        self.assertEqual(self.inbox_files(), ["绝对.txt"])
        self.assertIn("绝对路径", r.err)

    def test_rejects_missing_file(self):
        r = self.rejected("move", "--to", "材料", "没有.txt")
        self.assertIn("没有.txt", r.err)

    def test_rejects_unknown_destination(self):
        self.put("a.txt")
        r = self.cli("move", "--to", "文书", "a.txt")
        self.assertEqual(r.code, 2, r)
        self.assertEqual(self.inbox_files(), ["a.txt"])

    def test_never_writes_statement_dir(self):
        self.put("律师陈述/伪.md")
        r = self.rejected("move", "--to", "材料", "律师陈述/伪.md")
        self.assertFalse((self.ws / "材料" / "律师陈述").exists())
        self.assertIn("律师陈述", r.err)
        self.rejected("move", "--to", "材料", "律师陈述")
        self.assertFalse((self.ws / "材料" / "律师陈述").exists())

    def test_zip_and_photo_go_to_materials_as_is(self):
        zip_bytes = b"PK\x03\x04not-really-a-zip"
        self.put("包.zip", zip_bytes)
        self.put("照片.JPG", b"\xff\xd8\xff")
        self.ok("move", "--to", "材料", "包.zip", "照片.JPG")
        self.assertEqual((self.ws / "材料" / "包.zip").read_bytes(), zip_bytes, "压缩包原样，不解压")
        self.assertTrue((self.ws / "材料" / "照片.JPG").is_file())
        self.assertEqual(sorted(p.name for p in (self.ws / "材料").iterdir()), ["包.zip", "照片.JPG"])

    def test_zip_and_photo_refuse_other_destinations(self):
        self.put("包.zip")
        self.put("照片.png")
        for dest in ("指南", "模板/官方", "模板/生成"):
            r = self.rejected("move", "--to", dest, "包.zip")
            self.assertIn("材料", r.err)
            self.rejected("move", "--to", dest, "照片.png")
        self.assertEqual(self.inbox_files(), ["包.zip", "照片.png"])

    def test_directory_containing_photo_refuses_other_destinations(self):
        self.put("照片夹/说明.txt")
        self.put("照片夹/深/x.JPG")
        r = self.rejected("move", "--to", "指南", "照片夹")
        self.assertIn("照片夹/深/x.JPG", r.err)
        self.assertEqual(self.inbox_files(), ["照片夹/深/x.JPG", "照片夹/说明.txt"])
        self.ok("move", "--to", "材料", "照片夹")
        self.assertTrue((self.ws / "材料" / "照片夹" / "深" / "x.JPG").is_file())

    def test_dot_prefixed_relative_path_is_accepted(self):
        self.put("a.txt")
        self.ok("move", "--to", "材料", "./a.txt")
        self.assertTrue((self.ws / "材料" / "a.txt").is_file())

    def test_requires_workspace_marker(self):
        other = pathlib.Path(tempfile.mkdtemp(prefix="filing-nows-"))
        self.addCleanup(shutil.rmtree, other, True)
        (other / "收件箱").mkdir()
        (other / "收件箱" / "a.txt").write_bytes(b"a")
        r = self.rejected("move", "--to", "材料", "a.txt", workspace=other)
        self.assertIn("图.json", r.err)
        self.assertTrue((other / "收件箱" / "a.txt").is_file())

    def test_does_not_touch_graph(self):
        self.put("a.txt")
        self.ok("move", "--to", "材料", "a.txt")
        self.assertEqual((self.ws / "图.json").read_text(encoding="utf-8"), "{}")


class ListTest(ArchiveCase):
    def test_lists_relative_paths_recursively(self):
        self.put("b.txt")
        self.put("甲方/2025/a.pdf")
        r = self.ok("list")
        self.assertEqual(r.out.splitlines(), ["b.txt", "甲方/2025/a.pdf"])

    def test_empty_inbox(self):
        r = self.ok("list")
        self.assertIn("收件箱为空", r.out)
        shutil.rmtree(self.inbox)
        r = self.ok("list")
        self.assertIn("收件箱为空", r.out)


if __name__ == "__main__":
    unittest.main()
