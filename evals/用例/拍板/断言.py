"""拍板用例的断言：确认落在对的节点、原话原样存、已确认的节点不适用被引擎拒。签名 (workspace: Path, reply: str)。"""
import json

确认的 = "管理人印章备案报告"
已确认的 = "管理人承诺书及团队人员"


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _node(workspace, title):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] == title:
                return n
    raise AssertionError("图里没有节点「%s」" % title)


def check_确认条目落在印章备案上(workspace, reply):
    entries = _node(workspace, 确认的)["条目"]
    assert len(entries) == 2, "该节点该是种子那条生成加这次的确认，实际 %s" % [e["动作"] for e in entries]
    e = entries[-1]
    assert e["动作"] == "确认", "末条该是确认，实际 %r" % e["动作"]
    assert e["来源"] == "律师", "确认的来源恒为律师，实际 %r" % e["来源"]


def check_原话原样存(workspace, reply):
    words = _node(workspace, 确认的)["条目"][-1].get("原话", "")
    assert words, "确认条目没有原话（留痕规则 a）"
    assert "就这样" in words or "确认" in words, "原话该是律师那句话，不是模型自己的话，实际 %r" % words


def check_已确认的节点不适用被拒(workspace, reply):
    entries = _node(workspace, 已确认的)["条目"]
    动作 = [e["动作"] for e in entries]
    assert 动作 == ["生成", "确认"], "已确认的节点不能不适用，条目不该多出一条，实际 %s" % 动作


def check_别的节点没被动过(workspace, reply):
    for m in _graph(workspace)["模块"]:
        for n in m["节点"]:
            if n["标题"] in (确认的, 已确认的):
                continue
            assert n["条目"] == [], "节点「%s」不该有条目：%s" % (n["标题"], n["条目"])


def check_视图重算了(workspace, reply):
    md = (workspace / "图视图.md").read_text(encoding="utf-8")
    words = _node(workspace, 确认的)["条目"][-1]["原话"]
    assert words in md, "图视图.md 该显示确认的原话，缺 %r" % words
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    n = next(x for m in view["模块"] for x in m["节点"] if x["标题"] == 确认的)
    assert n["状态"] == "已确认" and "最近确认" in n, "视图该把它算成已确认：%s" % n


def check_回复给了下一句(workspace, reply):
    assert "doit" in reply or "新对话" in reply, "收尾没说下一句该打什么：\n%s" % reply
