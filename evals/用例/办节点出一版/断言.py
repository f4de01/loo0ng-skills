"""办节点出一版用例的断言：两版各三件、条目路径为准、陈述落了并被引、收尾两行。

签名 (workspace: Path, reply: str)。
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
GATE = REPO / "skills" / "in-progress" / "to-docx" / "scripts" / "gate.py"
节点 = "管理人银行账户备案报告"
模板 = "1-3.关于管理人银行账户备案的报告.docx"
种子里的陈述 = 2


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def _生成条目(workspace):
    return [e for e in _node(workspace, 节点)["条目"] if e["动作"] == "生成"]


def check_出了两版每版三件(workspace, reply):
    d = workspace / "文书" / 节点
    assert d.is_dir(), "没有 文书/%s/" % 节点
    docx = sorted(p.name for p in d.glob("*.docx"))
    assert len(docx) == 2, "该出两版（先照出一版，补了事实再出一版），实际 %s" % docx
    for name in docx:
        stem = name[:-len(".docx")]
        assert (d / (stem + ".md")).is_file(), "缺 Markdown 源 %s.md" % stem
        assert (d / (stem + "-审查报告.md")).is_file(), "每一版文书必有一份审查报告，缺 %s-审查报告.md" % stem
    stray = [p.name for p in d.iterdir() if p.suffix not in (".docx", ".md")]
    assert stray == [], "文书目录里多出了东西：%s" % stray


def check_两条生成条目的路径都指着真在的文件(workspace, reply):
    entries = _生成条目(workspace)
    assert len(entries) == 2, "该追加两条生成条目，实际 %s" % entries
    for e in entries:
        assert e["来源"] == "agent", "工作台出的件来源该是 agent，实际 %r" % e["来源"]
        for key in ("文书", "源", "审查报告"):
            rel = e.get(key)
            assert rel, "生成条目缺 %s：%s" % (key, e)
            assert (workspace / rel).is_file(), "条目里的 %s 指着不存在的文件：%s" % (key, rel)
            assert rel.startswith("文书/%s/" % 节点), "%s 该落在 文书/<节点标题>/ 下，实际 %r" % (key, rel)


def _门禁(workspace, rel):
    """在临时副本上跑门禁：门禁起的 Word 会多攥一会儿刚检过的件，跑器就删不掉工作区（#32）。"""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gate-check-"))
    try:
        copy = tmp / pathlib.Path(rel).name
        shutil.copy2(workspace / rel, copy)
        r = subprocess.run([sys.executable, str(GATE), str(copy),
                            "--template", str(workspace / "模板" / "官方" / 模板), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode != 2, "门禁没跑起来：%s" % r.stderr.strip()  # 0 通过 / 3 需人眼 / 1 不通过都算跑起来了
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_落盘的两件重跑门禁都通过(workspace, reply):
    for e in _生成条目(workspace):
        result = _门禁(workspace, e["文书"])
        assert result["结论"] == "通过", "落盘的件门禁不通过：%s %s" % (e["文书"], result["不通过项"])


def check_口头事实落成了陈述(workspace, reply):
    files = sorted((workspace / "材料" / "律师陈述").glob("*.md"))
    assert len(files) == 种子里的陈述 + 1, \
        "对话里给的事实该先落成一条陈述再用，实际 %s" % [p.name for p in files]
    new = [p for p in files if "甲银行" in p.read_text(encoding="utf-8")]
    assert new, "新陈述里没有律师那句话的内容：%s" % [p.name for p in files]
    text = new[0].read_text(encoding="utf-8")
    assert "## 原话" in text, "陈述缺原话段：\n%s" % text
    assert "性质:" in text, "陈述缺性质字段：\n%s" % text


def check_第二版审查报告引了那条陈述(workspace, reply):
    e = _生成条目(workspace)[-1]
    text = (workspace / e["审查报告"]).read_text(encoding="utf-8")
    assert "[律师陈述" in text, "第二版的审查报告该按格式引用律师陈述：\n%s" % text
    assert "材料/律师陈述/" in text, "引用该给出陈述文件的相对路径：\n%s" % text


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，确认永不自动，实际 %s" % 动作
    assert _node(workspace, 节点)["条目"][-1]["动作"] == "生成", "本节点末条该还是生成，等律师拍板"


def check_收尾两行(workspace, reply):
    assert "确认" in reply or "拍板" in reply, "收尾第一行没说本节点在本对话里拍板：\n%s" % reply
    assert "新对话" in reply or "doit" in reply, "收尾第二行没说下一个节点开新对话：\n%s" % reply


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not (p.name == "__pycache__" or p.name.startswith(".")))
    assert names == ["AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md",
                     "指南", "收件箱", "文书", "材料", "模板"], \
        "工作区根多出了东西（转换与门禁在临时位置完成，工作区里不建暂存目录）：%s" % names


def check_文书目录只多了这一个(workspace, reply):
    dirs = sorted(p.name for p in (workspace / "文书").iterdir() if p.is_dir())
    assert dirs == ["管理人印章备案报告", "管理人承诺书及团队人员", 节点], "文书/ 下多了目录：%s" % dirs
