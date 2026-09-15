"""拒改收尾用例的断言：生成失败什么都没留下（不落盘、不写审查报告、不追加条目），模板没被改，回复交出拒改原文并提兜底。

签名 (workspace: Path, reply: str)。
"""
import hashlib
import json
import pathlib
import re

节点 = "管理人银行账户备案报告"
节点目录 = "文书/接受指定与报备/管理人银行账户备案报告"
模板名 = "1-3.关于管理人银行账户备案的报告.docx"
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "归档索引.md", "待归档", "材料", "参考", "文书"}


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_一件都没落盘(workspace, reply):
    d = workspace / 节点目录
    有 = sorted(p.name for p in d.rglob("*")) if d.exists() else []
    assert 有 == [], "生成失败不落盘、不写审查报告，节点目录下却有：%s" % 有
    docs = sorted(p.relative_to(workspace).as_posix() for p in (workspace / "文书").rglob("*") if p.is_file())
    assert all(p.startswith(("文书/接受指定与报备/管理人承诺书及团队人员/", "文书/接受指定与报备/管理人印章备案报告/")) for p in docs), \
        "文书/ 下只该有种子那两个节点的东西，实际 %s" % docs


def check_没追加条目(workspace, reply):
    assert _node(workspace, 节点)["条目"] == [], "生成失败不追加条目，实际 %s" % _node(workspace, 节点)["条目"]
    assert [e["动作"] for e in _node(workspace, "管理人印章备案报告")["条目"]] == ["生成"], "别的节点被动了"
    assert [e["动作"] for e in _node(workspace, "管理人承诺书及团队人员")["条目"]] == ["生成", "确认"], "别的节点被动了"
    动作 = [e["动作"] for m in _graph(workspace)["模块"] for n in m["节点"] for e in n["条目"]]
    assert 动作 == ["生成", "确认", "生成"], "图上只该有种子那三条条目，实际 %s" % 动作


def check_模板没被改(workspace, reply):
    """拒因在模板里（域代码），绕开它的唯一办法是改模板：改的是差量、不是模板规定的正文结构（SKILL.md）。"""
    p = workspace / "参考" / "模板" / 模板名
    assert p.is_file(), "模板原件不见了"
    import zipfile
    with zipfile.ZipFile(str(p)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "instrText" in xml, "模板里钉的域代码被拿掉了：模型改了模板来绕过拒改"
    assert sorted(x.name for x in (workspace / "参考" / "模板").iterdir() if x.name.endswith(".docx")).count(模板名) == 1
    assert len([x for x in (workspace / "参考" / "模板").iterdir()]) == 19, "参考/模板 里多出了东西（不许另造一份模板绕过）"


def check_回复交出拒改并提兜底(workspace, reply):
    """别拿「高亮了哪几处」当反面判据：那是收尾第二段的小标题，生成失败这一回合照样要有（写这一版没有文书）。"""
    assert re.search(r"拒改|拒绝|生成失败|域代码", reply), "回复该把拒改原文交给律师、说明生成失败：\n%s" % reply
    # 兜底那条路律师那句话有好几种说法（doit 正文举的是「X 我自己写好了」「X 用我这份」），都收。
    assert re.search(r"兜底|自己写|自写|自行填写|自己填|用我这份", reply), \
        "回复该告诉律师可以兜底自写（在 Word 里填完交给我、用我这份）：\n%s" % reply
    assert not re.search(r"已写出 ?文书/|已追加生成条目", reply), "生成失败却报成出件了：\n%s" % reply


def check_没往工作区乱写(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区根多出了东西（差量与中间件写临时位置，失败的件不进工作区）：%s" % 多
