"""scripts/skill-eval.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/skill-eval/test_skill_eval.py

不调用真实的 claude / codex：后端可执行文件由 harness_executable() 解析，测试把它换成
本地的假脚本（吐固定 JSON 或 JSONL）；工作区生命周期用注入的假 invoke 验证。
"""
import importlib.util
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "skill-eval.py"

spec = importlib.util.spec_from_file_location("skill_eval", SCRIPT)
skill_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill_eval)

PASSING_CHECKS = textwrap.dedent('''
    def helper(x):
        return x

    def check_文件内容(workspace, reply):
        assert (workspace / "冒烟.txt").read_text(encoding="utf-8") == "冒烟通过"

    def check_回复有句号(workspace, reply):
        assert reply.endswith("。"), "回复应以句号结尾"
''')


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def make_case(root, name, *, prompt="写文件", checks=PASSING_CHECKS, **meta):
    meta.setdefault("种子", "")
    meta.setdefault("回复正则", "")
    d = root / name
    write(d, "提示词.md", prompt)
    write(d, "断言.py", checks)
    write(d, "用例.json", json.dumps(meta, ensure_ascii=False))
    return d


class ParseArgsTest(unittest.TestCase):
    def test_harness_choices(self):
        with self.assertRaises(SystemExit):
            skill_eval.parse_args(["--harness", "gemini"])

    def test_defaults(self):
        a = skill_eval.parse_args(["--harness", "claude"])
        self.assertEqual(a.harness, "claude")
        self.assertEqual(a.runs, 1)
        self.assertEqual(a.case, [])
        self.assertIsNone(a.max_turns)
        self.assertIsNone(a.timeout)
        self.assertFalse(a.keep)
        self.assertEqual(pathlib.Path(a.evals), pathlib.Path("evals") / "用例")

    def test_runs_must_be_positive(self):
        with self.assertRaises(SystemExit):
            skill_eval.parse_args(["--harness", "codex", "--runs", "0"])

    def test_case_is_repeatable(self):
        a = skill_eval.parse_args(["--harness", "codex", "--case", "冒烟", "--case", "甲", "--runs", "3"])
        self.assertEqual(a.case, ["冒烟", "甲"])
        self.assertEqual(a.runs, 3)


class LoadCaseTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_loads_fields(self):
        d = make_case(self.root, "冒烟", prompt="写一个文件\n", 回复正则=r"已写入", 回合上限=5, 超时秒=60,
                      skill="doit", 允许工具=["Bash(python *)"], 说明="冒烟")
        case = skill_eval.load_case(d)
        self.assertEqual(case.name, "冒烟")
        self.assertEqual(case.prompt, "写一个文件")
        self.assertEqual(case.seed, "")
        self.assertEqual(case.skill, "doit")
        self.assertEqual(case.reply_re, r"已写入")
        self.assertEqual(case.max_turns, 5)
        self.assertEqual(case.timeout, 60)
        self.assertEqual(case.allowed_tools, ["Bash(python *)"])
        self.assertEqual(len(case.checks), 2)

    def test_skill_requires_a_description(self):
        d = make_case(self.root, "有skill无说明", skill="doit")
        with self.assertRaises(skill_eval.EvalError) as cm:
            skill_eval.load_case(d)
        self.assertIn("说明", str(cm.exception))

    def test_missing_assertion_file_is_an_error(self):
        d = make_case(self.root, "缺断言")
        (d / "断言.py").unlink()
        with self.assertRaises(skill_eval.EvalError):
            skill_eval.load_case(d)

    def test_unknown_key_is_an_error(self):
        d = make_case(self.root, "错键", 回复正则表达式="x")
        with self.assertRaises(skill_eval.EvalError) as cm:
            skill_eval.load_case(d)
        self.assertIn("回复正则表达式", str(cm.exception))

    def test_codex_sandbox_defaults_and_validates(self):
        d = make_case(self.root, "默认沙箱")
        self.assertEqual(skill_eval.load_case(d).codex_sandbox, "workspace-write")
        d = make_case(self.root, "全权", Codex沙箱="danger-full-access")
        self.assertEqual(skill_eval.load_case(d).codex_sandbox, "danger-full-access")
        d = make_case(self.root, "错沙箱", Codex沙箱="read-only")
        with self.assertRaises(skill_eval.EvalError) as cm:
            skill_eval.load_case(d)
        self.assertIn("Codex沙箱", str(cm.exception))

    def test_missing_required_key_is_an_error(self):
        d = self.root / "缺键"
        write(d, "提示词.md", "p")
        write(d, "断言.py", PASSING_CHECKS)
        write(d, "用例.json", json.dumps({"种子": ""}))
        with self.assertRaises(skill_eval.EvalError) as cm:
            skill_eval.load_case(d)
        self.assertIn("回复正则", str(cm.exception))

    def test_discover_filters_and_sorts(self):
        make_case(self.root, "乙")
        make_case(self.root, "甲")
        (self.root / "不是用例").mkdir()
        names = [c.name for c in skill_eval.discover_cases(self.root, [])]
        self.assertEqual(names, ["乙", "甲"])
        names = [c.name for c in skill_eval.discover_cases(self.root, ["甲"])]
        self.assertEqual(names, ["甲"])
        with self.assertRaises(skill_eval.EvalError):
            skill_eval.discover_cases(self.root, ["丙"])


class LoadAssertionsTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_collects_check_functions_in_definition_order(self):
        p = write(self.root, "断言.py", PASSING_CHECKS)
        checks = skill_eval.load_assertions(p)
        self.assertEqual([n for n, _ in checks], ["check_文件内容", "check_回复有句号"])
        for _, fn in checks:
            self.assertTrue(callable(fn))

    def test_no_check_function_is_an_error(self):
        p = write(self.root, "断言.py", "def helper():\n    pass\n")
        with self.assertRaises(skill_eval.EvalError):
            skill_eval.load_assertions(p)

    def test_syntax_error_is_an_error(self):
        p = write(self.root, "断言.py", "def check_a(:\n")
        with self.assertRaises(skill_eval.EvalError):
            skill_eval.load_assertions(p)

    def test_two_files_do_not_share_namespace(self):
        a = skill_eval.load_assertions(write(self.root, "a/断言.py", "def check_a(w, r):\n    pass\n"))
        b = skill_eval.load_assertions(write(self.root, "b/断言.py", "def check_b(w, r):\n    pass\n"))
        self.assertEqual([n for n, _ in a], ["check_a"])
        self.assertEqual([n for n, _ in b], ["check_b"])


class PromptAndCommandTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_prompt_without_skill_is_verbatim_on_both(self):
        case = skill_eval.load_case(make_case(self.root, "a", prompt="写一个文件"))
        self.assertEqual(skill_eval.build_prompt("claude", case), "写一个文件")
        self.assertEqual(skill_eval.build_prompt("codex", case), "写一个文件")

    def test_codex_uses_stand_in_prompt_for_skill(self):
        """Codex 侧的替身提示词照新根写（0.154 起 ~/.codex/skills），两个根都没有这件时也是它。"""
        case = skill_eval.load_case(make_case(self.root, "a", prompt="帮我起手", skill="setup-case", 说明="替身"))
        原 = skill_eval.CODEX_SKILL_ROOTS
        skill_eval.CODEX_SKILL_ROOTS = (self.root / "无-codex", self.root / "无-agents")
        self.addCleanup(setattr, skill_eval, "CODEX_SKILL_ROOTS", 原)
        p = skill_eval.build_prompt("codex", case)
        self.assertIn("无-codex/setup-case/SKILL.md", p.replace("\\", "/"))
        self.assertTrue(p.endswith("帮我起手"))
        self.assertEqual(skill_eval.build_prompt("claude", case), "/loo0ng-skills:setup-case 帮我起手")
        self.assertEqual(skill_eval.build_prompt("claude", case, ""), "/setup-case 帮我起手")

    def test_codex_stand_in_falls_back_to_the_old_root_when_that_is_where_the_skill_is(self):
        """0.153 及更早的机器上 skill 在 ~/.agents/skills 下，替身提示词得跟着指过去。"""
        case = skill_eval.load_case(make_case(self.root, "b", prompt="帮我起手", skill="setup-case", 说明="替身"))
        旧根 = self.root / "旧根"
        (旧根 / "setup-case").mkdir(parents=True)
        (旧根 / "setup-case" / "SKILL.md").write_text("x", encoding="utf-8")
        原 = skill_eval.CODEX_SKILL_ROOTS
        skill_eval.CODEX_SKILL_ROOTS = (self.root / "无-codex", 旧根)
        self.addCleanup(setattr, skill_eval, "CODEX_SKILL_ROOTS", 原)
        p = skill_eval.build_prompt("codex", case)
        self.assertIn("旧根/setup-case/SKILL.md", p.replace("\\", "/"))

    def test_claude_plugin_follows_whether_the_plugin_is_installed(self):
        """照上游一个 harness 只装一条路：装了插件带命名空间，改造期走 junction 就是裸名（ADR-0022）；
        与 scripts/link-skills.ps1 认同一个文件。显式给了 --claude-plugin 以它为准。"""
        installed = self.root / "installed_plugins.json"
        原 = skill_eval.INSTALLED_PLUGINS
        skill_eval.INSTALLED_PLUGINS = installed
        self.addCleanup(setattr, skill_eval, "INSTALLED_PLUGINS", 原)
        self.assertEqual(skill_eval.parse_args(["--harness", "claude"]).claude_plugin, "", "文件不在：裸名")
        installed.write_text('{"plugins": {"loo0ng-skills@loo0ng-marketplace": {}}}', encoding="utf-8")
        self.assertEqual(skill_eval.parse_args(["--harness", "claude"]).claude_plugin, "loo0ng-skills")
        installed.write_text('{"plugins": {"other@x": {}}}', encoding="utf-8")
        self.assertEqual(skill_eval.parse_args(["--harness", "claude"]).claude_plugin, "")
        self.assertEqual(skill_eval.parse_args(["--harness", "claude", "--claude-plugin", "mine"]).claude_plugin, "mine")
        self.assertEqual(skill_eval.parse_args(["--harness", "claude", "--claude-plugin", ""]).claude_plugin, "")

    def test_claude_command(self):
        ws = self.root / "ws"
        cmd = skill_eval.build_command("claude", ["claude.exe"], "提示", ws, max_turns=7,
                                      last_path=self.root / "last.md", allowed_tools=["Bash(python *)"])
        self.assertEqual(cmd[0], "claude.exe")
        self.assertIn("-p", cmd)
        self.assertIn("提示", cmd)
        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "7")
        self.assertEqual(cmd[cmd.index("--output-format") + 1], "json")
        self.assertEqual(cmd[cmd.index("--allowedTools") + 1], "Bash(python *)")

    def test_codex_command(self):
        ws = self.root / "ws"
        last = self.root / "last.md"
        cmd = skill_eval.build_command("codex", ["codex.cmd"], "提示", ws, max_turns=7,
                                      last_path=last, allowed_tools=[])
        self.assertEqual(cmd[:2], ["codex.cmd", "exec"])
        self.assertIn("--json", cmd)
        self.assertIn("--skip-git-repo-check", cmd)
        self.assertEqual(cmd[cmd.index("-C") + 1], str(ws))
        self.assertEqual(cmd[cmd.index("-o") + 1], str(last))
        self.assertEqual(cmd[-1], "-", "提示词走 stdin，PROMPT 位置是 -")
        self.assertNotIn("提示", cmd)
        self.assertEqual(cmd[cmd.index("-s") + 1], "workspace-write")

    def test_codex_command_takes_the_case_sandbox(self):
        cmd = skill_eval.build_command("codex", ["codex.cmd"], "提示", self.root / "ws", max_turns=7,
                                      last_path=self.root / "last.md", allowed_tools=[], codex_sandbox="danger-full-access")
        self.assertEqual(cmd[cmd.index("-s") + 1], "danger-full-access")
        claude = skill_eval.build_command("claude", ["claude.cmd"], "提示", self.root / "ws", max_turns=7,
                                          last_path=self.root / "last.md", allowed_tools=[], codex_sandbox="danger-full-access")
        self.assertNotIn("danger-full-access", claude, "Claude Code 侧不受这个键影响")

    def test_model_and_effort_are_passed_through(self):
        """两侧各自的写法：Claude Code 侧 --model/--effort，Codex 侧 -m 加一条 -c 配置覆盖（#105 附带）。"""
        claude = skill_eval.build_command("claude", ["claude.exe"], "提示", self.root / "ws", max_turns=7,
                                          last_path=self.root / "last.md", allowed_tools=[],
                                          model="opus", effort="high")
        self.assertEqual(claude[claude.index("--model") + 1], "opus")
        self.assertEqual(claude[claude.index("--effort") + 1], "high")
        codex = skill_eval.build_command("codex", ["codex.cmd"], "提示", self.root / "ws", max_turns=7,
                                         last_path=self.root / "last.md", allowed_tools=[],
                                         model="gpt-5", effort="high")
        self.assertEqual(codex[codex.index("-m") + 1], "gpt-5")
        self.assertEqual(codex[codex.index("-c") + 1], 'model_reasoning_effort="high"')
        self.assertEqual(codex[-1], "-", "提示词仍走 stdin，PROMPT 位置还是 -")

    def test_no_model_no_flags(self):
        """两个参数都不给时命令与从前逐字相同：走各自 CLI 的默认，这是既有跑法的兼容线。"""
        for harness, exe in (("claude", ["claude.exe"]), ("codex", ["codex.cmd"])):
            cmd = skill_eval.build_command(harness, exe, "提示", self.root / "ws", max_turns=7,
                                           last_path=self.root / "last.md", allowed_tools=[])
            for flag in ("--model", "--effort", "-m", "-c"):
                self.assertNotIn(flag, cmd, "%s 侧不该凭空多出 %s：%s" % (harness, flag, cmd))

    def test_env_strips_nested_claude_and_disables_msys_pathconv(self):
        env = skill_eval.harness_env({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli", "PATH": "x"})
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_CODE_ENTRYPOINT", env)
        self.assertEqual(env["MSYS_NO_PATHCONV"], "1")
        self.assertEqual(env["PATH"], "x")


def fake_invoke(status="ok", reply="已写入冒烟.txt。", turns=2, files=None, seen=None):
    def invoke(harness, case, workspace, prompt, max_turns, timeout, model=None, effort=None):
        if seen is not None:
            seen.append((workspace, prompt, max_turns, timeout, sorted(p.name for p in workspace.iterdir())))
        for rel, text in (files or {}).items():
            write(workspace, rel, text)
        return skill_eval.Invocation(status=status, reply=reply, turns=turns, detail="")
    return invoke


class WorkspaceTest(unittest.TestCase):
    def test_workspace_is_under_tempdir_with_case_name(self):
        ws = skill_eval.make_workspace("冒烟")
        self.addCleanup(skill_eval.remove_workspace, ws)
        self.assertTrue(ws.is_dir())
        self.assertEqual(ws.parent, pathlib.Path(tempfile.gettempdir()))
        self.assertTrue(ws.name.startswith("skill-eval-冒烟-"))
        self.assertEqual(list(ws.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "ACL 只在 Windows 上有意义")
    def test_workspace_acl_includes_current_user(self):
        """mkdtemp 在 Windows 上建的目录没有本用户的 ACE，Codex 沙箱写的文件会读不了；mkdir 继承 %TEMP% 的。"""
        import subprocess
        ws = skill_eval.make_workspace("acl")
        self.addCleanup(skill_eval.remove_workspace, ws)
        r = subprocess.run(["icacls", str(ws)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertIn("\%s:" % os.environ["USERNAME"], r.stdout, r.stdout)

    def test_remove_workspace_clears_readonly_files(self):
        ws = skill_eval.make_workspace("rm")
        f = write(ws, "只读.txt", "x")
        os.chmod(f, 0o444)
        skill_eval.remove_workspace(ws)
        self.assertFalse(ws.exists())


class RunCaseLifecycleTest(unittest.TestCase):
    def setUp(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.root = tmp / "用例"  # 种子在旁边的 tmp/种子，与 evals/用例、evals/种子 同构
        self.root.mkdir()

    def opts(self, **kw):
        return skill_eval.parse_args(["--harness", "claude", "--evals", str(self.root), *kw.pop("argv", [])])

    def test_workspace_is_fresh_and_removed_after_pass(self):
        case = skill_eval.load_case(make_case(self.root, "冒烟", 回复正则=r"已写入冒烟\.txt"))
        seen = []
        results = skill_eval.run_case(case, self.opts(), invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed, results[0].failures)
        ws, prompt, max_turns, timeout, before = seen[0]
        self.assertEqual(before, [])
        self.assertFalse(ws.exists())
        self.assertNotEqual(ws.parent, self.root)

    def test_workspace_removed_after_failure_and_names_the_assertion(self):
        case = skill_eval.load_case(make_case(self.root, "故意失败", 回复正则=r"已写入"))
        seen = []
        results = skill_eval.run_case(case, self.opts(), invoke=fake_invoke(files={"冒烟.txt": "写错了"}, seen=seen))
        self.assertFalse(results[0].passed)
        self.assertEqual([f.name for f in results[0].failures], ["check_文件内容"])
        self.assertFalse(seen[0][0].exists())

    def test_reply_regex_failure_is_named(self):
        case = skill_eval.load_case(make_case(self.root, "正则", 回复正则=r"^完成$"))
        results = skill_eval.run_case(case, self.opts(), invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}))
        self.assertEqual([f.name for f in results[0].failures], ["回复正则"])

    def test_workspace_removed_when_invoke_raises(self):
        case = skill_eval.load_case(make_case(self.root, "炸"))
        seen = []

        def boom(harness, case, workspace, prompt, max_turns, timeout, model=None, effort=None):
            seen.append(workspace)
            raise RuntimeError("harness 炸了")

        with self.assertRaises(RuntimeError):
            skill_eval.run_case(case, self.opts(), invoke=boom)
        self.assertFalse(seen[0].exists())

    def test_timeout_and_max_turns_status_fail_without_running_checks(self):
        case = skill_eval.load_case(make_case(self.root, "超时"))
        for status in ("timeout", "max_turns"):
            results = skill_eval.run_case(case, self.opts(), invoke=fake_invoke(status=status, reply=""))
            self.assertFalse(results[0].passed)
            self.assertEqual([f.name for f in results[0].failures], ["harness:" + status])

    def test_keep_leaves_workspace(self):
        case = skill_eval.load_case(make_case(self.root, "留"))
        seen = []
        skill_eval.run_case(case, self.opts(argv=["--keep"]), invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        ws = seen[0][0]
        self.assertTrue(ws.exists())
        shutil.rmtree(ws)
        for 家 in pathlib.Path(tempfile.gettempdir()).glob("skill-eval-留-家-*"):
            shutil.rmtree(家, ignore_errors=True)

    def test_每次运行给一个临时的家(self):
        """个人预设图本来住 ~/.loo0ng/预设图/（ADR-0023）；eval 不往律师的主目录里写东西，也不吃上一次跑剩下的预设图。"""
        case = skill_eval.load_case(make_case(self.root, "家"))
        家 = []

        def 记下(harness, c, workspace, prompt, max_turns, timeout, model=None, effort=None):
            家.append(os.environ.get(skill_eval.HOME_ENV))
            return skill_eval.Invocation(status="ok", reply="", turns=1, detail="")

        旧 = os.environ.pop(skill_eval.HOME_ENV, None)
        self.addCleanup(lambda: os.environ.__setitem__(skill_eval.HOME_ENV, 旧)
                        if 旧 is not None else None)
        skill_eval.run_case(case, self.opts(argv=["--runs", "2"]), invoke=记下)
        self.assertEqual(len(家), 2)
        self.assertTrue(all(家), "每次运行都要经 %s 给一个家：%s" % (skill_eval.HOME_ENV, 家))
        self.assertEqual(len(set(家)), 2, "两次运行不该共用一个家：%s" % 家)
        for 路径 in 家:
            self.assertFalse(pathlib.Path(路径).exists(), "跑完要连家一起删（只生不存）")
        self.assertIsNone(os.environ.get(skill_eval.HOME_ENV), "跑完要把环境变量还原")

    def test_runs_n_uses_a_new_workspace_each_time(self):
        case = skill_eval.load_case(make_case(self.root, "多跑"))
        seen = []
        results = skill_eval.run_case(case, self.opts(argv=["--runs", "3"]),
                                      invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(len(results), 3)
        self.assertEqual(len({s[0] for s in seen}), 3)
        self.assertEqual([s[4] for s in seen], [[], [], []])

    def test_cli_limits_override_case_limits(self):
        case = skill_eval.load_case(make_case(self.root, "限", 回合上限=5, 超时秒=9))
        seen = []
        skill_eval.run_case(case, self.opts(), invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(seen[0][2:4], (5, 9))
        seen.clear()
        skill_eval.run_case(case, self.opts(argv=["--max-turns", "2", "--timeout", "3"]),
                            invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(seen[0][2:4], (2, 3))

    def test_seed_is_replayed_into_workspace_before_invoke(self):
        seeds = self.root.parent / "种子"
        write(seeds, "空目录/收件箱/合同.md", "甲公司")
        write(seeds, "空目录/状态.md", "说明")
        write(seeds, "空目录/回放.py", "import pathlib, sys\n(pathlib.Path(sys.argv[1]) / '图.json').write_text('{}')\n")
        case = skill_eval.load_case(make_case(self.root, "有种子", 种子="空目录"))
        seen = []
        skill_eval.run_case(case, self.opts(), invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(seen[0][4], ["图.json", "收件箱"])
        self.assertFalse(seen[0][0].exists())

    def test_seed_replay_works_with_relative_evals_root(self):
        """回放在工作区里跑，evals 根是相对路径（默认值就是）时种子也要找得到（#26 首次用种子时发现）。"""
        seeds = self.root.parent / "种子"
        write(seeds, "相对/状态.md", "说明")
        write(seeds, "相对/回放.py", "import pathlib, sys\n(pathlib.Path(sys.argv[1]) / '图.json').write_text('{}')\n")
        case = skill_eval.load_case(make_case(self.root, "相对根", 种子="相对"))
        cwd = os.getcwd()
        os.chdir(self.root.parent.parent)
        self.addCleanup(os.chdir, cwd)
        rel = os.path.relpath(self.root, self.root.parent.parent)
        seen = []
        skill_eval.run_case(case, self.opts(argv=["--evals", rel]),
                            invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}, seen=seen))
        self.assertEqual(seen[0][4], ["图.json"])

    def test_missing_seed_is_an_error_and_workspace_removed(self):
        case = skill_eval.load_case(make_case(self.root, "无种子", 种子="不存在"))
        with self.assertRaises(skill_eval.EvalError):
            skill_eval.run_case(case, self.opts(), invoke=fake_invoke())


FAKE_CLAUDE = textwrap.dedent('''
    import json, pathlib, sys, time
    args = sys.argv[1:]
    prompt = args[args.index("-p") + 1]
    if "sleep" in prompt:
        time.sleep(30)
    if "turns" in prompt:
        print(json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 9,
                          "errors": ["Reached maximum number of turns (1)"]}))
        sys.exit(0)
    pathlib.Path("冒烟.txt").write_text("冒烟通过", encoding="utf-8")
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 3,
                      "result": "已写入冒烟.txt。"}, ensure_ascii=False))
''')

FAKE_CODEX = textwrap.dedent('''
    import json, pathlib, sys, time
    args = sys.argv[1:]
    prompt = sys.stdin.read() if args[-1] == "-" else args[-1]  # 真 codex：PROMPT 为 "-" 时从 stdin 读
    ws = pathlib.Path(args[args.index("-C") + 1])
    last = pathlib.Path(args[args.index("-o") + 1])
    (ws / "收到的提示词.txt").write_text(prompt, encoding="utf-8")
    def emit(o):
        print(json.dumps(o, ensure_ascii=False), flush=True)
    emit({"type": "thread.started", "thread_id": "t"})
    emit({"type": "turn.started"})
    if "quota" in prompt:
        emit({"type": "error", "message": "You've hit your usage limit. try again at Sep 6th"})
        emit({"type": "turn.failed", "error": {"message": "You've hit your usage limit. try again at Sep 6th"}})
        sys.exit(1)
    n = 12 if "turns" in prompt else 1
    for i in range(n):
        emit({"type": "item.started", "item": {"id": "i%d" % i, "type": "file_change", "status": "in_progress"}})
        emit({"type": "item.completed", "item": {"id": "i%d" % i, "type": "file_change", "status": "completed"}})
        if "turns" in prompt:
            time.sleep(0.5)  # 给跑器 2 秒的 taskkill 等待留余量：超回合后须在写出文件前被杀
    if "sleep" in prompt:
        time.sleep(30)
    (ws / "冒烟.txt").write_text("冒烟通过", encoding="utf-8")
    emit({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": "已写入冒烟.txt。"}})
    emit({"type": "turn.completed", "usage": {}})
    last.write_text("已写入冒烟.txt。", encoding="utf-8")
''')


class RealInvokeWithFakeBinariesTest(unittest.TestCase):
    """走真实的子进程、超时与回合上限逻辑，只把 claude / codex 换成假脚本。"""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ws = self.root / "ws"
        self.ws.mkdir()
        fake_claude = write(self.root, "fake_claude.py", FAKE_CLAUDE)
        fake_codex = write(self.root, "fake_codex.py", FAKE_CODEX)
        self.orig = skill_eval.harness_executable
        skill_eval.harness_executable = lambda h: [sys.executable, str(fake_claude if h == "claude" else fake_codex)]
        self.addCleanup(setattr, skill_eval, "harness_executable", self.orig)
        self.case = skill_eval.load_case(make_case(self.root, "c"))

    def test_claude_success(self):
        inv = skill_eval.invoke("claude", self.case, self.ws, "写", max_turns=5, timeout=20)
        self.assertEqual(inv.status, "ok", inv.detail)
        self.assertEqual(inv.reply, "已写入冒烟.txt。")
        self.assertEqual(inv.turns, 3)
        self.assertEqual((self.ws / "冒烟.txt").read_text(encoding="utf-8"), "冒烟通过")

    def test_codex_stream_error_is_surfaced(self):
        """codex 的错误在 JSONL 流里（如用量上限），stderr 只有一句 stdin 提示；detail 须带流里的消息（#26）。"""
        inv = skill_eval.invoke("codex", self.case, self.ws, "quota", max_turns=5, timeout=20)
        self.assertEqual(inv.status, "error")
        self.assertIn("usage limit", inv.detail)

    def test_claude_max_turns(self):
        inv = skill_eval.invoke("claude", self.case, self.ws, "turns", max_turns=1, timeout=20)
        self.assertEqual(inv.status, "max_turns")
        self.assertEqual(inv.turns, 9)

    def test_claude_timeout_kills_process(self):
        import time
        t0 = time.monotonic()
        inv = skill_eval.invoke("claude", self.case, self.ws, "sleep", max_turns=5, timeout=1)
        self.assertEqual(inv.status, "timeout")
        self.assertLess(time.monotonic() - t0, 15)

    def test_codex_success(self):
        inv = skill_eval.invoke("codex", self.case, self.ws, "写", max_turns=5, timeout=20)
        self.assertEqual(inv.status, "ok", inv.detail)
        self.assertEqual(inv.reply, "已写入冒烟.txt。")
        self.assertEqual(inv.turns, 1)
        self.assertEqual(sorted(p.name for p in self.ws.iterdir()), ["冒烟.txt", "收到的提示词.txt"])
        leftovers = [p.name for p in pathlib.Path(tempfile.gettempdir()).glob("skill-eval-c-out-*")]
        self.assertEqual(leftovers, [], "-o 输出目录应随调用结束删除")

    def test_codex_multiline_prompt_arrives_intact_via_stdin(self):
        """PATH 上的 codex 是 .cmd 垫片，参数里的换行会被 cmd.exe 吞掉，所以提示词走 stdin（#28）。"""
        prompt = "第一行：\n\n# 标题\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n:right: 落款\n"
        inv = skill_eval.invoke("codex", self.case, self.ws, prompt, max_turns=5, timeout=20)
        self.assertEqual(inv.status, "ok", inv.detail)
        self.assertEqual((self.ws / "收到的提示词.txt").read_text(encoding="utf-8"), prompt)

    def test_codex_max_turns_kills_process(self):
        inv = skill_eval.invoke("codex", self.case, self.ws, "turns", max_turns=3, timeout=20)
        self.assertEqual(inv.status, "max_turns")
        self.assertGreater(inv.turns, 3)
        self.assertFalse((self.ws / "冒烟.txt").exists())

    def test_codex_timeout_kills_process(self):
        import time
        t0 = time.monotonic()
        inv = skill_eval.invoke("codex", self.case, self.ws, "sleep", max_turns=5, timeout=1)
        self.assertEqual(inv.status, "timeout")
        self.assertLess(time.monotonic() - t0, 15)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_exit_codes(self):
        import io
        make_case(self.root, "过", 回复正则="已写入")
        out = io.StringIO()
        rc = skill_eval.main(["--harness", "claude", "--evals", str(self.root)],
                             invoke=fake_invoke(files={"冒烟.txt": "冒烟通过"}), out=out)
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("PASS", out.getvalue())
        self.assertIn("模型 CLI 默认", out.getvalue(), "跨跑比较要读得出这次是哪个模型跑的")
        rc = skill_eval.main(["--harness", "claude", "--evals", str(self.root)],
                             invoke=fake_invoke(files={"冒烟.txt": "错"}), out=out)
        self.assertEqual(rc, 1)
        self.assertIn("check_文件内容", out.getvalue())
        rc = skill_eval.main(["--harness", "claude", "--evals", str(self.root / "没有")], invoke=fake_invoke(), out=out)
        self.assertEqual(rc, 2)


class MaterializeTest(unittest.TestCase):
    """--materialize <种子>：只生一个工作区回放种子、打印路径就停，不跑 harness、不删。

    关票触发要在这样的工作区上做（#66：只生不存），没有这条命令规矩就落不实。
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="skill-eval-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.用例根 = self.tmp / "evals" / "用例"
        self.用例根.mkdir(parents=True)
        种子 = self.tmp / "evals" / "种子" / "小种子"
        种子.mkdir(parents=True)
        write(种子, "状态.md", "这一份不该被拷进工作区")
        write(种子, "收件箱/一件.txt", "种子带进来的")
        write(种子, "回放.py", textwrap.dedent('''
            import pathlib, sys
            (pathlib.Path(sys.argv[1]) / "回放留下的.txt").write_text("ok", encoding="utf-8")
        '''))
        self.生出的 = []

    def 跑(self, argv):
        buf = io.StringIO()
        code = skill_eval.main(argv, out=buf)
        for line in buf.getvalue().splitlines():
            p = pathlib.Path(line.strip())
            if p.is_absolute() and p.is_dir():
                self.生出的.append(p)
                self.addCleanup(skill_eval.remove_workspace, p)
        return code, buf.getvalue()

    def test_不必给_harness(self):
        opts = skill_eval.parse_args(["--materialize", "小种子"])
        self.assertEqual(opts.materialize, "小种子")
        self.assertIsNone(opts.harness)

    def test_两者都不给仍是用法错(self):
        with self.assertRaises(SystemExit) as e:
            skill_eval.parse_args([])
        self.assertEqual(e.exception.code, 2)

    def test_两者都给也是用法错(self):
        with self.assertRaises(SystemExit) as e:
            skill_eval.parse_args(["--materialize", "小种子", "--harness", "claude"])
        self.assertEqual(e.exception.code, 2)

    def test_跑用例才有意义的参数一并互斥(self):
        for 多余 in (["--case", "冒烟"], ["--runs", "2"], ["--keep"],
                     ["--max-turns", "5"], ["--timeout", "60"]):
            with self.subTest(多余=多余):
                with self.assertRaises(SystemExit) as e:
                    skill_eval.parse_args(["--materialize", "小种子", *多余])
                self.assertEqual(e.exception.code, 2)

    def test_回放种子并打印工作区路径(self):
        code, 输出 = self.跑(["--materialize", "小种子", "--evals", str(self.用例根)])
        self.assertEqual(code, 0, 输出)
        self.assertEqual(len(self.生出的), 1, "该打印恰一行工作区路径：\n%s" % 输出)
        ws = self.生出的[0]
        self.assertEqual((ws / "收件箱" / "一件.txt").read_text(encoding="utf-8"), "种子带进来的")
        self.assertEqual((ws / "回放留下的.txt").read_text(encoding="utf-8"), "ok")
        self.assertFalse((ws / "状态.md").exists(), "种子的元文件不进工作区")

    def test_家在工作区里的种子回显出要设的家(self):
        """回放自己兜底管不到 harness 里的模型：它调 preset.py 时没有这个变量就读写真的 ~/.loo0ng（#105）。"""
        种子 = self.tmp / "evals" / "种子" / "带个人预设图的"
        种子.mkdir(parents=True)
        write(种子, "回放.py", textwrap.dedent('''
            import pathlib, sys
            (pathlib.Path(sys.argv[1]) / ".预设图家" / "预设图" / "菜园").mkdir(parents=True)
        '''))
        code, 输出 = self.跑(["--materialize", "带个人预设图的", "--evals", str(self.用例根)])
        self.assertEqual(code, 0, 输出)
        ws = self.生出的[0]
        self.assertIn("%s=%s" % (skill_eval.HOME_ENV, ws / skill_eval.WS_HOME), 输出,
                      "该回显触发之前要设的家：\n%s" % 输出)

    def test_家不在工作区里的种子不多回显一行(self):
        code, 输出 = self.跑(["--materialize", "小种子", "--evals", str(self.用例根)])
        self.assertEqual(code, 0, 输出)
        self.assertNotIn(skill_eval.HOME_ENV, 输出, "没有个人预设图的种子照旧只打印一行路径")

    def test_工作区不被删掉(self):
        code, 输出 = self.跑(["--materialize", "小种子", "--evals", str(self.用例根)])
        self.assertEqual(code, 0, 输出)
        self.assertTrue(self.生出的[0].is_dir(), "生出来就是给人接着用的，不能跑完就删")

    def test_种子不存在是用法错(self):
        code, _ = self.跑(["--materialize", "没这个种子", "--evals", str(self.用例根)])
        self.assertEqual(code, 2)

if __name__ == "__main__":
    unittest.main()
