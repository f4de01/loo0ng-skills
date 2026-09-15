"""模块不适用用例的断言：模块里每个节点各一条不适用、来源律师、原话原样存、别的模块没动。签名 (workspace: Path, reply: str)。"""
import json

模块 = "自行和解"
节点们 = ("和解协议", "裁定认可和解协议并终结破产程序的申请")


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _module(workspace, title):
    for m in _graph(workspace)["模块"]:
        if m["标题"] == title:
            return m
    raise AssertionError("图里没有模块「%s」" % title)


def check_模块里每个节点各一条不适用(workspace, reply):
    m = _module(workspace, 模块)
    assert [n["标题"] for n in m["节点"]] == list(节点们), "模块构成不该变：%s" % [n["标题"] for n in m["节点"]]
    for n in m["节点"]:
        动作 = [e["动作"] for e in n["条目"]]
        assert 动作 == ["不适用"], "「%s」该恰有一条不适用，实际 %s" % (n["标题"], 动作)
        assert n["条目"][0]["来源"] == "律师", "不适用的来源恒为律师"
        原话 = n["条目"][0].get("原话", "")
        assert "不走和解" in 原话 or "不适用" in 原话, "原话该是律师那句话，实际 %r" % 原话


def check_别的模块没动(workspace, reply):
    for m in _graph(workspace)["模块"]:
        if m["标题"] == 模块:
            continue
        for n in m["节点"]:
            动作 = [e["动作"] for e in n["条目"]]
            if n["标题"] == "管理人承诺书及团队人员":
                assert 动作 == ["生成", "确认"], "承诺书不该被动：%s" % 动作
            elif n["标题"] == "管理人印章备案报告":
                assert 动作 == ["生成"], "印章备案不该被动：%s" % 动作
            else:
                assert 动作 == [], "节点「%s」不该有条目：%s" % (n["标题"], 动作)


def check_视图算成模块不适用(workspace, reply):
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    m = next(x for x in view["模块"] if x["标题"] == 模块)
    assert m["状态"] == "不适用", "模块状态该是不适用，实际 %r" % m["状态"]
    前方 = [x["标题"] for mm in view["前方"] for x in mm["节点"]]
    assert not any(t in 前方 for t in 节点们), "不适用的节点不该还在前方里：%s" % 前方
