"""scripts/link-skills.ps1 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/link-skills/test_link_skills.py

在临时目录里造一个假仓库（git init + skills/<name>/SKILL.md）与两个假的用户级 skill 目录，
用 -Repo / -Dests 两个参数把脚本指过去，断言 junction 的存在与去向。
不碰真实的 ~/.claude/skills 与 ~/.agents/skills。只在 Windows 上有意义：junction 是 NTFS 的东西。
"""
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "link-skills.ps1"
BOM = b"\xef\xbb\xbf"


def is_reparse(path):
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False
    return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def run_link(repo, dests):
    dest_list = ",".join("'%s'" % d for d in dests)
    cmd = "& '%s' -Repo '%s' -Dests @(%s)" % (SCRIPT, repo, dest_list)
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def make_skill(repo, name, bucket="productivity"):
    """skills/<bucket>/<name>/SKILL.md，桶照上游；链接名只取 <name>。"""
    d = repo / "skills" / bucket / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: test\n---\n" % name, encoding="utf-8")
    return d


@unittest.skipUnless(sys.platform == "win32", "junction 只在 Windows 上存在")
class LinkSkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="link-skills-"))
        self.repo = self.tmp / "repo"
        (self.repo / "skills").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.dests = [self.tmp / "claude-skills", self.tmp / "agents-skills"]

    def tearDown(self):
        # 先拆 junction 再删树，免得 rmtree 顺着链接进目标。
        for d in self.dests:
            if d.exists():
                for child in d.iterdir():
                    if is_reparse(child):
                        os.rmdir(child)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assert_ok(self, r):
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def links_in(self, dest):
        return sorted(p.name for p in dest.iterdir() if is_reparse(p)) if dest.exists() else []

    def test_script_has_utf8_bom(self):
        self.assertEqual(SCRIPT.read_bytes()[:3], BOM)

    def test_links_every_skill_into_both_dests(self):
        make_skill(self.repo, "loo0ng-alpha")
        make_skill(self.repo, "loo0ng-beta")
        r = run_link(self.repo, self.dests)
        self.assert_ok(r)
        for d in self.dests:
            self.assertEqual(self.links_in(d), ["loo0ng-alpha", "loo0ng-beta"])
            self.assertTrue((d / "loo0ng-alpha" / "SKILL.md").is_file())

    def test_sets_hooks_path(self):
        make_skill(self.repo, "loo0ng-alpha")
        run_link(self.repo, self.dests)
        out = subprocess.run(["git", "-C", str(self.repo), "config", "core.hooksPath"],
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), ".githooks")

    def test_idempotent_second_run_same_result(self):
        make_skill(self.repo, "loo0ng-alpha")
        first = run_link(self.repo, self.dests)
        self.assert_ok(first)
        before = {d: self.links_in(d) for d in self.dests}
        second = run_link(self.repo, self.dests)
        self.assert_ok(second)
        after = {d: self.links_in(d) for d in self.dests}
        self.assertEqual(before, after)
        self.assertTrue((self.dests[0] / "loo0ng-alpha" / "SKILL.md").is_file())

    def test_removed_skill_loses_its_junction(self):
        make_skill(self.repo, "loo0ng-alpha")
        gone = make_skill(self.repo, "loo0ng-gone")
        run_link(self.repo, self.dests)
        shutil.rmtree(gone)
        r = run_link(self.repo, self.dests)
        self.assert_ok(r)
        for d in self.dests:
            self.assertEqual(self.links_in(d), ["loo0ng-alpha"])
            self.assertFalse((d / "loo0ng-gone").exists())

    def test_leaves_foreign_entries_alone(self):
        make_skill(self.repo, "loo0ng-alpha")
        foreign_dir = self.dests[0] / "someone-else"
        foreign_dir.mkdir(parents=True)
        (foreign_dir / "SKILL.md").write_text("x", encoding="utf-8")
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        subprocess.run(["cmd", "/c", "mklink", "/J", str(self.dests[0] / "foreign-link"), str(elsewhere)],
                       check=True, capture_output=True)
        r = run_link(self.repo, self.dests)
        self.assert_ok(r)
        self.assertTrue((foreign_dir / "SKILL.md").is_file())
        self.assertTrue(is_reparse(self.dests[0] / "foreign-link"))
        self.assertIn("loo0ng-alpha", self.links_in(self.dests[0]))

    def test_skips_deprecated_and_misc_buckets_like_upstream(self):
        make_skill(self.repo, "loo0ng-alpha", "productivity")
        make_skill(self.repo, "loo0ng-beta", "in-progress")
        make_skill(self.repo, "loo0ng-old", "deprecated")
        make_skill(self.repo, "loo0ng-rare", "misc")
        r = run_link(self.repo, self.dests)
        self.assert_ok(r)
        for d in self.dests:
            self.assertEqual(self.links_in(d), ["loo0ng-alpha", "loo0ng-beta"],
                             "照上游 link-skills.sh：deprecated/ 与 misc/ 不挂，in-progress/ 照挂")

    def test_readme_only_skills_dir_links_nothing(self):
        (self.repo / "skills" / "README.md").write_text("x", encoding="utf-8")
        r = run_link(self.repo, self.dests)
        self.assert_ok(r)
        for d in self.dests:
            self.assertEqual(self.links_in(d), [])

    def test_refuses_dest_that_is_link_into_repo(self):
        make_skill(self.repo, "loo0ng-alpha")
        bad = self.tmp / "bad-dest"
        subprocess.run(["cmd", "/c", "mklink", "/J", str(bad), str(self.repo / "skills")],
                       check=True, capture_output=True)
        r = run_link(self.repo, [bad])
        os.rmdir(bad)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
