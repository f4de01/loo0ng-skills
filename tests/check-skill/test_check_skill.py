"""通过 CLI 验证 skill 布局与兄弟参考文件的自足性检查。"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[2]


class CheckSkillTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.skill = self.root / "skills" / "engineering" / "sample"
        (self.skill / "agents").mkdir(parents=True)
        (self.skill / "scripts").mkdir()
        (self.skill / "SKILL.md").write_text(
            '---\nname: sample\ndescription: "示例"\n---\n'
            '[格式](./FORMAT.md)\n', encoding="utf-8")
        (self.skill / "FORMAT.md").write_text("# 格式\n", encoding="utf-8")
        (self.skill / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: sample\n  short_description: 示例\n',
            encoding="utf-8")

    def check(self):
        bash = shutil.which("bash")
        env = dict(os.environ)
        env["PYTHON"] = sys.executable
        if os.name == "nt":
            git = pathlib.Path(shutil.which("git"))
            git_root = git.parent.parent
            bash = str(git_root / "bin" / "bash.exe")
            env["PATH"] = str(git_root / "usr" / "bin") + os.pathsep + env["PATH"]
        return subprocess.run(
            [bash, str(REPO / "scripts" / "check-skill.sh"), str(self.root)],
            capture_output=True, text=True, encoding="utf-8", env=env)

    def test_sibling_reference_and_allowed_directories_pass(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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


if __name__ == "__main__":
    unittest.main()
