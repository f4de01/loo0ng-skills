"""兜底登记用例的断言：文书没被改动、条目来源律师、审查报告五段齐全且门禁只有披露项。

签名 (workspace: Path, reply: str)。
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
GATE = REPO / "skills" / "productivity" / "to-docx" / "scripts" / "gate.py"
节点 = "管理人印章备案报告"
成品 = "印章备案-我自己写的.docx"
模板 = "1-2.关于管理人印章备案的报告.docx"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def _成品路径(workspace):
    found = [p for p in workspace.rglob(成品)]
    assert len(found) == 1, "工作区里该恰有一份律师自写的成品，实际 %s" % [str(p) for p in found]
    return found[0]


def check_文书登记为已生成来源律师(workspace, reply):
    entries = _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in entries] == ["生成", "生成"], \
        "该在种子那条生成之后再追加一条生成，实际 %s" % [e["动作"] for e in entries]
    e = entries[-1]
    assert e["来源"] == "律师", "兜底件的来源该记律师，实际 %r" % e["来源"]
    doc = workspace / e["文书"]
    assert doc.is_file(), "条目里的文书路径指着不存在的文件：%s" % e["文书"]
    assert doc.name == 成品, "条目该指着律师那份成品，实际 %r" % e["文书"]
    assert doc == _成品路径(workspace), "条目里的路径与成品实际所在不一致"


def check_成品没被改动也没重转(workspace, reply):
    doc = _成品路径(workspace)
    assert doc.parent.name != "收件箱", "归档之后不该还留在收件箱：%s" % doc
    # 门禁跑在临时副本上：它起的 Word 会多攥一会儿刚检过的件，跑器就删不掉工作区（#32）。
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gate-check-"))
    try:
        copy = tmp / doc.name
        shutil.copy2(doc, copy)
        r = subprocess.run([sys.executable, str(GATE), str(copy),
                            "--template", str(workspace / "模板" / "官方" / 模板), "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode != 2, "门禁没跑起来：%s" % r.stderr.strip()  # 0 通过 / 3 需人眼 / 1 不通过都算跑起来了
        result = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert result["结论"] == "通过", "律师那份本来过得了门禁，现在不过了：%s" % result["不通过项"]
    assert result["披露项"], "这份该有披露项（印模那格是空的）"


def check_审查报告落在文书目录下且五段齐全(workspace, reply):
    e = _node(workspace, 节点)["条目"][-1]
    rel = e["审查报告"]
    assert rel.startswith("文书/%s/" % 节点), "审查报告该落在 文书/<节点标题>/ 下，实际 %r" % rel
    text = (workspace / rel).read_text(encoding="utf-8")
    for heading in ("## 生成依据", "## 存疑点", "## 待律师裁定", "## 版式门禁", "## 时限"):
        assert heading in text, "审查报告缺固定段 %s：\n%s" % (heading, text)
    门禁段 = text.split("## 版式门禁", 1)[1].split("## 时限", 1)[0]
    assert "披露" in 门禁段, "门禁段该照抄门禁的披露项：\n%s" % 门禁段
    assert "通过" in 门禁段, "门禁段该有结论：\n%s" % 门禁段


def check_没有节点被自动确认(workspace, reply):
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作.count("确认") == 1, "只该有种子里承诺书那一条确认，确认永不自动，实际 %s" % 动作


def check_收件箱清了(workspace, reply):
    left = sorted(p.name for p in (workspace / "收件箱").rglob("*"))
    assert left == [], "开场归档该把收件箱清空，实际还剩 %s" % left
