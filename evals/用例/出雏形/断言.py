"""出雏形用例的断言：图里多了指南提的三个节点、同名的没重复、案件图没写时限、视图重算、没留雏形文件。

签名 (workspace: Path, reply: str)。
"""
import json

新模块 = "越冬"
新节点 = ("覆膜", "清园", "施追肥")
已有的 = "浇水"
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "归档索引.md", "待归档", "材料", "参考", "文书"}


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def _graph(workspace):
    return json.loads((workspace / "图.json").read_text(encoding="utf-8"))


def _nodes(data):
    return [(m, n) for m in data["模块"] for n in m["节点"]]


def check_图里多了指南提的节点(workspace, reply):
    data = _graph(workspace)
    模块 = [m["标题"] for m in data["模块"]]
    assert 新模块 in 模块, "指南里的新模块「%s」没进图：%s" % (新模块, 模块)
    titles = [n["标题"] for _, n in _nodes(data)]
    for t in 新节点:
        assert t in titles, "指南里的「%s」没进图：%s" % (t, titles)
    所在 = {n["标题"]: m["标题"] for m, n in _nodes(data)}
    assert 所在["覆膜"] == 新模块 and 所在["清园"] == 新模块, "覆膜与清园该在新模块「%s」下：%s" % (新模块, 所在)
    assert 所在["施追肥"] == "养护", "施追肥该挂在已有模块「养护」下，实际 %r" % 所在["施追肥"]


def check_同名的没重复(workspace, reply):
    titles = [n["标题"] for _, n in _nodes(_graph(workspace))]
    assert titles.count(已有的) == 1, "「%s」图里已经有，不该再提、再建：%s" % (已有的, titles)
    assert len(titles) == len(set(titles)), "图里有重名节点：%s" % titles
    assert len(titles) == 12, "9 个原有加 3 个新提的，该恰是 12 个：%s" % titles


def check_案件图没写时限(workspace, reply):
    for _, n in _nodes(_graph(workspace)):
        if n["标题"] in 新节点:
            assert not n.get("时限"), "案件图上的时限只回显不写（引擎拒），「%s」却写了 %r" % (n["标题"], n["时限"])
    assert all(n["条目"] == [] for _, n in _nodes(_graph(workspace))), "雏形不该写条目"


def check_视图重算了(workspace, reply):
    md = (workspace / "图视图.md").read_text(encoding="utf-8")
    for t in (新模块,) + 新节点:
        assert t in md, "图视图.md 里没有「%s」，视图没随写图重算" % t
    view = json.loads((workspace / "图视图.json").read_text(encoding="utf-8"))
    前方 = [x["标题"] for m in view["前方"] for x in m["节点"]]
    assert all(t in 前方 for t in 新节点), "新节点都未生成，该在前方里：%s" % 前方


def check_没留雏形文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "雏形文件该写在临时位置，工作区根多出了：%s" % 多


def check_回显里有新提的(workspace, reply):
    for t in (新模块,) + 新节点:
        assert t in reply, "回显清单里没有「%s」：\n%s" % (t, reply)
