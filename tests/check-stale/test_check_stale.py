"""scripts/check-stale.sh 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/check-stale -p 'test_*.py'

守两件事：
1. 名单口径与 check-text.sh、check-skill.sh 一致：已跟踪 + 未被忽略的未跟踪，问 git 要。
   原先这里手写着一份 `--exclude-dir` 名单，它与 .gitignore 各走各的，迟早分叉。
2. 语义上的例外与「被忽略」是两回事：CHANGELOG.md 与 .changeset/ 本来就该记旧名（放过），
   docs/ 下提到旧名只提醒不失败，其余任何位置提到即失败。
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-stale.sh"

sys.path.insert(0, str(REPO / "tests" / "共用"))
from 临时仓库 import GitRepoMixin  # noqa: E402
from bash import find_bash  # noqa: E402

BASH, BASH_PATH_DIRS = find_bash()
OLD = "旧名字"


def run_check(root, env, old=OLD):
    env = dict(env)
    if BASH_PATH_DIRS:
        env["PATH"] = os.pathsep.join(BASH_PATH_DIRS + [env["PATH"]])
    proc = subprocess.run(
        [BASH, str(SCRIPT), ".", old], cwd=root, env=env, capture_output=True)
    out = proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")
    return proc.returncode, out


@unittest.skipIf(BASH is None, "机器上没有 bash")
class CheckStaleTests(GitRepoMixin, unittest.TestCase):
    def check(self):
        return run_check(self.root, self.env)

    def test_clean_repo_passes(self):
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("没有残留引用", out)

    def test_untracked_reference_fails_before_add(self):
        self.write("README.md", "还在说 旧名字\n")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("README.md", out)

    def test_changelog_and_changeset_may_keep_the_old_name(self):
        self.write("CHANGELOG.md", "改名：旧名字 -> 新名字\n")
        self.write("packages/某件/CHANGELOG.md", "改名：旧名字 -> 新名字\n")
        self.write(".changeset/abc.md", "旧名字 改名\n")
        self.write("packages/某件/.changeset/abc.md", "旧名字 改名\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_docs_reference_only_warns(self):
        self.write("docs/engineering/新名字.md", "旧名字 去哪了：改名成了新名字\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("docs 页里提到旧名字", out)
        self.assertIn("docs/engineering/新名字.md", out)

    def test_ignored_file_is_not_a_stale_reference(self):
        """被忽略的产物提交不上去，不该算残留引用（原先靠手写 --exclude-dir 名单挡）。"""
        self.write(".gitignore", "产物/\n")
        self.write("产物/缓存.md", "旧名字\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("产物", out)

    def test_ignored_directory_is_not_a_leftover_skill_directory(self):
        """忽略规则写成通配，免得 .gitignore 自己成了那处残留引用。"""
        self.write(".gitignore", "旧*/\n")
        (self.root / "skills" / "engineering" / OLD).mkdir(parents=True)
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("没有名为 %s 的 skill 目录" % OLD, out)

    def test_remaining_skill_directory_fails(self):
        (self.root / "skills" / "engineering" / OLD).mkdir(parents=True)
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("目录仍然存在", out)

    def test_chinese_path_is_not_truncated(self):
        """全程 -z：按行读会读到加引号转义后的名字，那种文件会被静默跳过。"""
        rel = "文档/深一层/中文名字的稿子.md"
        self.write(rel, "还在说 旧名字\n")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("中文名字的稿子.md", out)

    def test_non_repository_directory_is_refused(self):
        """名单要靠 git 列，不是仓库就明说，别悄悄扫出一份口径不同的结果。"""
        with tempfile.TemporaryDirectory() as plain:
            code, out = run_check(pathlib.Path(plain), self.env)
        self.assertEqual(code, 2, out)
        self.assertIn("不是 git 仓库", out)


if __name__ == "__main__":
    unittest.main()
