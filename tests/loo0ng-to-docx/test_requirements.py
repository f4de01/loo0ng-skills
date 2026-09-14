"""随包分发的依赖清单是 python-docx 版本唯一的钉（#75 验收，ADR-0018）。

约束的对象是转换器的后端版本，不是哪个解释器：怎么拿到能跑转换器的环境归 agent，正文不写死；能守的
只有「装的是钉住的那个版本」与「实测到什么就报什么」。清单落在 skill 目录顶层（`requirements.txt`），
随两条安装路一起到律师机；仓库根上的清单到不了那里，所以不作数。

**任何一条断言都不许 skip**（ADR-0015：本体测试在任何机器上全绿，只有渲染层许 skip）。依赖钉不是渲染
层，而且它红的那一刻正是它唯一有价值的时刻。

四条：清单的形状是精确钉且只此一条依赖；这台机器上装的版本等于清单里的数；转换器回显里的版本取自运行
时而不是照抄清单常量（拿替身元数据跑一次，回显跟着替身走，且退出码仍是 0）；清单里的数与散文里写出它的
每一处（`SKILL.md`、`references/审查报告.md` 的样例、`docs/agents/skills.md` 的布局表、ADR-0018）一致。
另加一条守 stdout 契约：那一行恒常写、位置固定在第二行。

运行：python -m unittest tests/loo0ng-to-docx/test_requirements.py
"""
import importlib.metadata
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import support

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "productivity" / "loo0ng-to-docx"
MANIFEST = SKILL / "requirements.txt"
# 散文里每一份版本号副本都归这条断言管：钉子的价值全在「没有第二个会静默掉队的数」，多写一处就多一个洞。
# ADR 按编号 glob，不写死那个中文长文件名：ADR 改名时该红在断言上，不该红在读文件上。
PROSE = [SKILL / "SKILL.md", SKILL / "references" / "审查报告.md",
         REPO / "docs" / "agents" / "skills.md"] + sorted((REPO / "docs" / "adr").glob("0018-*.md"))
PACKAGE = "python-docx"
FAKE_VERSION = "9.9.9"


def manifest_requirements():
    """清单里的依赖行：去掉注释与空行之后剩下的那些。

    故意不调转换器的 `pinned_version()`：那个只找第一条 python-docx，看不见清单里多出来的第二条依赖，
    而「只此一条」正是这里要验的。两边的解析各验各的，环境那一行的断言再把产品那一份带上。
    """
    lines = []
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def env_line(stdout):
    for line in stdout.splitlines():
        if line.startswith("出件环境："):
            return line
    return ""


class ManifestTest(unittest.TestCase):
    def test_manifest_pins_exactly_one_dependency_exactly(self):
        self.assertTrue(MANIFEST.is_file(), "依赖清单要在 skill 目录顶层：%s" % MANIFEST)
        reqs = manifest_requirements()
        self.assertEqual(len(reqs), 1, "清单只钉转换器那一个依赖，实际 %r" % reqs)
        self.assertRegex(reqs[0], r"^python-docx==\d+\.\d+\.\d+$",
                         "精确钉，不用区间：docx.oxml 那一层不作 SemVer 承诺（ADR-0018），实际 %r" % reqs[0])

    def test_installed_backend_is_the_pinned_one(self):
        pinned = manifest_requirements()[0].split("==", 1)[1]
        self.assertEqual(importlib.metadata.version(PACKAGE), pinned,
                         "这台机器上装的 python-docx 不是清单钉的那个版本，转换器的行为不再有依据")

    def test_pinned_number_is_the_same_number_everywhere_it_is_written_out(self):
        pinned = manifest_requirements()[0].split("==", 1)[1]
        self.assertEqual(len(PROSE), 4, "散文里那几处副本一处都不能漏，实际扫到 %r" % [p.name for p in PROSE])
        for path in PROSE:
            text = path.read_text(encoding="utf-8")
            found = set(re.findall(r"python-docx[=\s]*([0-9]+\.[0-9]+\.[0-9]+)", text))
            self.assertTrue(found, "%s 里没提 python-docx 的版本，钉子与正文对不上就没人发现" % path.name)
            self.assertEqual(found, {pinned},
                             "%s 里的版本 %r 与清单钉的 %s 不一致" % (path.name, sorted(found), pinned))


class ConverterReportsTest(unittest.TestCase):
    """转换器回显里的环境那一行：恒常写、取自运行时、版本对不上照跑。"""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="to-docx-req-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.md = self.dir / "稿.md"
        self.md.write_text("# 甲乙丙报告\n\n甲法院于甲年乙月丙日作出裁定。\n", encoding="utf-8")
        self.out = self.dir / "出件.docx"
        self.tpl = support.template("1-2.")

    def convert(self, env=None):
        r = subprocess.run(
            [sys.executable, str(support.CONVERTER), str(self.md), "--template", str(self.tpl),
             "--out", str(self.out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        return support.Run(r.returncode, r.stdout, r.stderr)

    def test_environment_line_is_always_printed_right_after_the_written_path(self):
        r = self.convert()
        self.assertEqual(r.code, 0, r)
        lines = r.out.splitlines()
        self.assertTrue(lines[0].startswith("已写出 "), r.out)
        self.assertTrue(lines[1].startswith("出件环境："), "环境那一行的位置固定在第二行，实际 %r" % r.out)
        self.assertIn(sys.executable, lines[1])
        self.assertIn(importlib.metadata.version(PACKAGE), lines[1])
        # 本机装的就是钉住的那个（上一条断言），所以这里该报「一致」：转换器自己那份清单解析也跟着被验了。
        self.assertIn("与依赖清单钉的一致", lines[1], lines[1])

    def test_reported_version_comes_from_the_runtime_not_the_manifest(self):
        """拿替身元数据跑一次：回显跟着替身走（说明取自运行时），照常出件（说明对不上不阻断）。"""
        shim = self.dir / "shim"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text(
            "import importlib.metadata as m\n"
            "_real = m.version\n"
            "m.version = lambda name, *a, **k: %r if name == %r else _real(name, *a, **k)\n"
            % (FAKE_VERSION, PACKAGE), encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(shim)
        r = self.convert(env=env)
        self.assertEqual(r.code, 0, "版本对不上照常出件，退出码不因此变成非零：%r" % r)
        self.assertTrue(self.out.is_file())
        line = env_line(r.out)
        self.assertIn(FAKE_VERSION, line, "回显里的版本照抄了清单常量，没去问运行时：%r" % line)
        pinned = manifest_requirements()[0].split("==", 1)[1]
        self.assertIn(pinned, line, "对不上时也要写出钉的是哪个数：%r" % line)
        self.assertIn("不是钉住的那个版本", line, "对不上时必须明写：%r" % line)


if __name__ == "__main__":
    unittest.main()
