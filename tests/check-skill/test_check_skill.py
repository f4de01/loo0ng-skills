"""通过 CLI 验证 skill 布局与兄弟参考文件的自足性检查。

两组用例，差别只在被扫的目录是不是 git 仓库：

- `CheckSkillTest` 用一个普通临时目录。它同时守着用法注释里那条仓库外的退路
  （`bash scripts/check-skill.sh ~/my-skills` 扫的目录不一定是 git 仓库）：探不到 git
  就不过滤、照旧全扫。
- `CheckSkillIgnoredTest` 用真 git 仓库，守名单口径：被 .gitignore 忽略的产物
  （跑一次测试就落下的 `__pycache__/`）不算布局违规，也不进扫 scripts/ 的那两条检查
  （正文随包自足、操作句只指向 model-invoked）；没被忽略的多余目录与文件仍旧要报。
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-skill.sh"

sys.path.insert(0, str(REPO / "tests" / "共用"))
from 临时仓库 import GitRepoMixin  # noqa: E402
from bash import find_bash  # noqa: E402

BASH, BASH_PATH_DIRS = find_bash()


def 摆一件skill(root):
    """在 root 下摆一件最小合法 skill，返回它的目录。"""
    skill = root / "skills" / "engineering" / "sample"
    (skill / "agents").mkdir(parents=True)
    (skill / "scripts").mkdir()
    (skill / "SKILL.md").write_text(
        '---\nname: sample\ndescription: "示例"\n---\n'
        '[格式](./FORMAT.md)\n', encoding="utf-8")
    (skill / "FORMAT.md").write_text("# 格式\n", encoding="utf-8")
    (skill / "agents" / "openai.yaml").write_text(
        'interface:\n  display_name: sample\n  short_description: 示例\n',
        encoding="utf-8")
    return skill


def 摆一件user_invoked的skill(root, name="hand"):
    """在 root 下再摆一件 user-invoked 的 skill：谁的操作句都不许指向它，只能叫人自己打。"""
    skill = root / "skills" / "engineering" / name
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        '---\nname: %s\ndescription: "律师自己打的那件"\n'
        'disable-model-invocation: true\n---\n' % name, encoding="utf-8")
    (skill / "agents" / "openai.yaml").write_text(
        'interface:\n  display_name: %s\n  short_description: 律师自己打的那件\n'
        'policy:\n  allow_implicit_invocation: false\n' % name, encoding="utf-8")
    return skill


def run_check(root, env=None):
    """跑 check-skill.sh 扫 root。"""
    env = dict(env if env is not None else os.environ)
    env["PYTHON"] = sys.executable
    if BASH_PATH_DIRS:
        env["PATH"] = os.pathsep.join(BASH_PATH_DIRS + [env["PATH"]])
    return subprocess.run(
        [BASH, str(SCRIPT), str(root)],
        capture_output=True, text=True, encoding="utf-8", env=env)


@unittest.skipIf(BASH is None, "机器上没有 bash")
class CheckSkillTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.skill = 摆一件skill(self.root)

    def check(self):
        return run_check(self.root)

    def test_sibling_reference_and_allowed_directories_pass(self):
        """这个目录不是 git 仓库：名单探不到 git 也要照旧扫完，不许报错退出。"""
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("fatal", result.stderr)

    def test_sibling_reference_is_checked_for_repository_dependencies(self):
        (self.skill / "FORMAT.md").write_text("请读 CONTEXT.md\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FORMAT.md:1", result.stdout)

    def test_unexpected_directories_fail_even_when_empty(self):
        (self.skill / "extra").mkdir()
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("extra", result.stdout)

    def test_scripts_are_checked_for_repository_dependencies(self):
        script = self.skill / "scripts" / "sample.py"
        for text in ('# 依据 ADR-0023\n', 'print("见 #54")\n',
                     '# 见 docs/guide.md\n', '# 发布版本 1.2.3\n'):
            with self.subTest(text=text):
                script.write_text(text, encoding="utf-8")
                result = self.check()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("scripts/sample.py:1", result.stdout)

    def test_scripts_keep_runtime_versions_coordinates_and_local_paths(self):
        (self.skill / "scripts" / "sample.py").write_text(
            '# python-docx==1.2.0; python 3.9.6\n'
            'FORMAT_VERSION = 2\n'
            '# 槽 p2#1；包内 ../FORMAT.md；工作区 AGENTS.md\n'
            'print("fill 要写槽号（如 p%d#1）" % 2)\n', encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_assets_are_data_even_when_markdown(self):
        payload = self.skill / "assets" / "preset" / "guides"
        payload.mkdir(parents=True)
        (payload / "guide.md").write_text("数据可以提到 CONTEXT.md\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_other_roles_cannot_nest(self):
        for role in ("agents", "scripts"):
            with self.subTest(role=role):
                nested = self.skill / role / "nested"
                nested.mkdir()
                result = self.check()
                nested.rmdir()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(role + "/nested", result.stdout)

    def test_asset_pointers_are_rejected_regardless_of_extension(self):
        original = (self.skill / "SKILL.md").read_text(encoding="utf-8")
        pointers = (
            "[读取](./assets/guide.md)",
            "[读取](assets/preset.json)",
            "[模板](<./assets/a template.docx>)",
            "[读取][data]\n[data]: ./assets/guide.md",
            "请读 `assets/guide.md`。",
            "[读取](./scripts/../assets/guide.md#section)",
            "[读取](./%61ssets/guide.md)",
            "[读取](file:///C:/skills/sample/assets/guide.md)",
            "[读取](C:/skills/sample/assets/guide.md)",
            "请读 `\\\\server\\share\\assets\\guide.md`。",
        )
        for pointer in pointers:
            with self.subTest(pointer=pointer):
                (self.skill / "SKILL.md").write_text(original + pointer + "\n", encoding="utf-8")
                result = self.check()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("数据目录", result.stdout)

    def test_data_location_description_and_external_url_are_not_pointers(self):
        with (self.skill / "SKILL.md").open("a", encoding="utf-8") as doc:
            doc.write('数据位于 `assets/预设图/<名>/`，按名经脚本解析。\n'
                      '目录位置：`assets/archive.d/`、`assets/release-1.0/`。\n'
                      '[网站](https://example.com/assets/guide.md)\n')
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipIf(BASH is None, "机器上没有 bash")
class CheckSkillIgnoredTest(GitRepoMixin, unittest.TestCase):
    """名单口径：工作树里的、未被忽略的。"""

    def setUp(self):
        super().setUp()
        self.skill = 摆一件skill(self.root)
        self.write(".gitignore", "__pycache__/\n产物/\n忽略.py\n")

    def check(self):
        return run_check(self.root, self.env)

    def test_clean_layout_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ignored_pycache_is_not_a_layout_violation(self):
        cache = self.skill / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "sample.cpython-313.pyc").write_bytes(b"\x00")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("__pycache__", result.stdout)

    def test_ignored_directory_with_chinese_name_is_not_truncated(self):
        """路径全程走 -z：改成按行喂 git，回来的是加引号转义后的名字，对不上就假红。"""
        (self.skill / "scripts" / "产物").mkdir()
        (self.skill / "产物").mkdir()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("产物", result.stdout)

    def test_unignored_extra_directory_still_fails(self):
        """本职不能一起放过：没被忽略的多余目录照旧是布局违规。"""
        (self.skill / "tmp").mkdir()
        (self.skill / "scripts" / "杂物").mkdir()
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("不允许的 skill 子目录", result.stdout)
        self.assertIn("tmp", result.stdout)
        self.assertIn("scripts/杂物", result.stdout)

    def test_ignored_script_is_not_scanned_for_repository_dependencies(self):
        (self.skill / "scripts" / "忽略.py").write_text("# 依据 ADR-0023\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_script_is_scanned_when_not_ignored(self):
        self.write(".gitignore", "__pycache__/\n")
        (self.skill / "scripts" / "忽略.py").write_text("# 依据 ADR-0023\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("scripts/忽略.py:1", result.stdout)

    def test_ignored_script_is_not_scanned_for_operative_sentences(self):
        """两处扫 scripts/ 的检查是一条名单：操作句那条也别去读被忽略的产物。"""
        摆一件user_invoked的skill(self.root)
        (self.skill / "scripts" / "忽略.py").write_text(
            '# 调用 Skill 工具，传 "hand"\n', encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_operative_sentence_is_scanned_when_not_ignored(self):
        self.write(".gitignore", "__pycache__/\n")
        摆一件user_invoked的skill(self.root)
        (self.skill / "scripts" / "忽略.py").write_text(
            '# 调用 Skill 工具，传 "hand"\n', encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("操作句指向了 user-invoked", result.stdout)

    def test_tracked_file_is_scanned_even_if_a_pattern_would_ignore_it(self):
        """跟踪了的文件不算被忽略：check-ignore 会看 index，别把入了库的东西漏掉。"""
        (self.skill / "scripts" / "忽略.py").write_text("# 依据 ADR-0023\n", encoding="utf-8")
        self.git("add", "-f", "skills/engineering/sample/scripts/忽略.py")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("scripts/忽略.py:1", result.stdout)


if __name__ == "__main__":
    unittest.main()
