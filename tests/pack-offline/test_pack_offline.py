"""scripts/pack-offline.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest discover -s tests/pack-offline -p 'test_*.py'
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "pack-offline.py"
LF = chr(10)
CRLF = chr(13) + chr(10)
BOM = bytes([0xEF, 0xBB, 0xBF])
# 带 CR、带 0 字节：转 LF 那一步碰它即露馅
二进制 = bytes([80, 75, 3, 4, 13, 10, 0, 255, 13])


def 跑(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, encoding="utf-8")


def 假仓库(根, 名单=("a-skill", "b-skill")):
    (根 / ".claude-plugin").mkdir(parents=True)
    (根 / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "x", "version": "0.0.0",
                    "skills": ["./skills/productivity/" + n for n in 名单]},
                   ensure_ascii=False, indent=2) + LF, encoding="utf-8")
    for n in 名单:
        d = 根 / "skills" / "productivity" / n
        (d / "scripts" / "__pycache__").mkdir(parents=True)
        (d / "assets").mkdir()
        (d / "SKILL.md").write_bytes(("---" + LF + "name: " + n + LF + "---" + LF + "正文" + LF).encode("utf-8"))
        (d / "scripts" / "cli.py").write_bytes(("print(1)" + CRLF).encode("utf-8"))
        (d / "scripts" / "__pycache__" / "cli.pyc").write_bytes(二进制)
        (d / "assets" / "模板.docx").write_bytes(二进制)
    return 根


class 打包(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.根 = 假仓库(pathlib.Path(self.tmp.name) / "repo")
        self.出 = pathlib.Path(self.tmp.name) / "out.zip"
        self.addCleanup(self.tmp.cleanup)

    def 打一次(self, *args):
        r = 跑("--root", str(self.根), "--zip", str(self.出), *args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return zipfile.ZipFile(self.出)

    def test_登记的每件都在包里且以skills为根(self):
        with self.打一次() as z:
            名单 = z.namelist()
        self.assertIn("skills/a-skill/SKILL.md", 名单)
        self.assertIn("skills/b-skill/SKILL.md", 名单)

    def test_文本一律转成LF(self):
        with self.打一次() as z:
            self.assertEqual(z.read("skills/a-skill/scripts/cli.py"), ("print(1)" + LF).encode("utf-8"))

    def test_二进制一个字节不改(self):
        with self.打一次() as z:
            self.assertEqual(z.read("skills/a-skill/assets/模板.docx"), 二进制)

    def test_不带pycache(self):
        with self.打一次() as z:
            self.assertEqual([n for n in z.namelist() if "__pycache__" in n], [])

    def test_BOM即停且不产出(self):
        p = self.根 / "skills" / "productivity" / "a-skill" / "SKILL.md"
        p.write_bytes(BOM + p.read_bytes())
        r = 跑("--root", str(self.根), "--zip", str(self.出))
        self.assertEqual(r.returncode, 1)
        self.assertIn("BOM", r.stderr)
        self.assertIn("a-skill", r.stderr)
        self.assertFalse(self.出.exists())

    def test_登记的目录不在即停(self):
        import shutil
        shutil.rmtree(self.根 / "skills" / "productivity" / "b-skill")
        r = 跑("--root", str(self.根), "--zip", str(self.出))
        self.assertEqual(r.returncode, 1)
        self.assertIn("b-skill", r.stderr)
        self.assertFalse(self.出.exists())

    def test_目录输出与zip同内容(self):
        目录 = pathlib.Path(self.tmp.name) / "兜底"
        r = 跑("--root", str(self.根), "--dir", str(目录))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((目录 / "a-skill" / "scripts" / "cli.py").read_bytes(), ("print(1)" + LF).encode("utf-8"))
        self.assertEqual((目录 / "b-skill" / "assets" / "模板.docx").read_bytes(), 二进制)
        self.assertFalse((目录 / "a-skill" / "scripts" / "__pycache__").exists())

    def test_目录非空即停(self):
        目录 = pathlib.Path(self.tmp.name) / "兜底"
        目录.mkdir()
        (目录 / "旧的").write_text("x", encoding="utf-8")
        r = 跑("--root", str(self.根), "--dir", str(目录))
        self.assertEqual(r.returncode, 1)
        self.assertIn("非空", r.stderr)

    def test_zip已经在了即停(self):
        self.出.write_bytes(b"old")
        r = 跑("--root", str(self.根), "--zip", str(self.出))
        self.assertEqual(r.returncode, 1)
        self.assertIn("已经在", r.stderr)
        self.assertEqual(self.出.read_bytes(), b"old")

    def test_目录那个位置是个文件即停(self):
        占位 = pathlib.Path(self.tmp.name) / "兜底"
        占位.write_text("x", encoding="utf-8")
        r = 跑("--root", str(self.根), "--dir", str(占位))
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)

    def test_没给出口即用法错(self):
        r = 跑("--root", str(self.根))
        self.assertEqual(r.returncode, 2)


class 真仓库(unittest.TestCase):
    def test_包里恰好是登记清单上的那几件(self):
        登记 = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["skills"]
        名单 = [p.rsplit("/", 1)[-1] for p in 登记]
        with tempfile.TemporaryDirectory() as tmp:
            出 = pathlib.Path(tmp) / "skills-offline.zip"
            r = 跑("--zip", str(出))
            self.assertEqual(r.returncode, 0, r.stderr)
            with zipfile.ZipFile(出) as z:
                条目 = z.namelist()
        顶层 = sorted({n.split("/")[1] for n in 条目})
        self.assertEqual(顶层, sorted(名单))
        for n in 名单:
            self.assertIn("skills/" + n + "/SKILL.md", 条目)


if __name__ == "__main__":
    unittest.main()
