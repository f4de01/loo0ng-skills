"""出一版用例的断言：文书/ 下恰一件 docx、门禁重跑通过、图没动。签名 (workspace: Path, reply: str)。"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
GATE = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "gate.py"
TEMPLATE_NAME = "1-2.关于管理人印章备案的报告.docx"


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、.uv-python 等），不算工作区产物。

    #105 实测 Codex 也会把 uv 的缓存落成不带点的 `uv-cache`，所以 `uv-` 开头的一并忽略：
    它是 harness 自备解释器留下的，不是 skill 的产物。七份同名小函数逐字相同，改一处就一起改。
    """
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def _docx_files(workspace):
    docs = workspace / "文书"
    return sorted(p for p in docs.rglob("*.docx")) if docs.is_dir() else []


def check_文书下恰一件docx(workspace, reply):
    files = _docx_files(workspace)
    assert len(files) == 1, "文书/ 下应恰有一件 docx，实际：%s" % [p.relative_to(workspace).as_posix() for p in files]
    assert files[0].relative_to(workspace).as_posix() == "文书/印章备案/印章备案-v1.docx", "落点不对：%s" % files[0]


def check_落盘的件重跑门禁通过(workspace, reply):
    docx = _docx_files(workspace)[0]
    template = workspace / "模板" / "官方" / TEMPLATE_NAME
    r = subprocess.run([sys.executable, str(GATE), str(docx), "--template", str(template), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode != 2, "门禁没跑起来：%s" % r.stderr.strip()  # 0 通过 / 3 需人眼 / 1 不通过都算跑起来了
    result = json.loads(r.stdout)
    assert result["结论"] == "通过", "落盘的件门禁不通过：%s" % result["不通过项"]
    body = "".join(t for t in _texts(docx))
    assert "乙公司管理人章" in body and "特此报告" in body, "正文没照稿子写"
    assert "XX" not in body, "模板占位符残留"


def _texts(docx):
    import zipfile
    import xml.etree.ElementTree as ET
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(str(docx)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return [t.text or "" for t in root.iter(w + "t")]


def check_模板原件没动_图没动(workspace, reply):
    template = workspace / "模板" / "官方" / TEMPLATE_NAME
    assert template.is_file(), "模板原件不见了"
    assert sorted(p.name for p in (workspace / "模板" / "官方").iterdir()) == [TEMPLATE_NAME], "模板/官方 里多了东西"
    data = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    assert all(n["条目"] == [] for m in data["模块"] for n in m["节点"]), "本用例没让写图，不该有条目"


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    allowed = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
               "收件箱", "材料", "指南", "模板", "文书"}  # 起手落下的六格，本用例里除 模板/ 外都是空的
    extra = [n for n in names if n not in allowed]
    assert extra == [], "工作区根多出了东西（转换与门禁应在临时位置完成，工作区里不建暂存目录）：%s" % extra
    docs = workspace / "文书" / "印章备案"
    stray = [p.name for p in docs.iterdir() if p.suffix not in (".docx", ".md")]
    assert stray == [], "文书目录里多出了东西：%s" % stray
