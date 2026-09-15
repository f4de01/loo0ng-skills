"""另存预设图用例的断言：个人预设图落在家里、剥掉条目、标题去案件化、模板拷走、案件图不动。

签名 (workspace: Path, reply: str)。家的路径从种子写的 .家.json 读。
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 基线 import 校验基线  # noqa: E402

新名 = "菜园二"
核心词 = "补种"
案件里的字 = ("乙家", "甲年乙月丙日")


def _家(workspace):
    p = workspace / ".家.json"
    assert p.is_file(), "种子没写下 .家.json，找不到个人预设图的根"
    return pathlib.Path(json.loads(p.read_text(encoding="utf-8"))["预设图根"])


def _预设图(workspace):
    d = _家(workspace) / 新名
    assert (d / "预设图.json").is_file(), "家里没有个人预设图「%s」（该在 %s）" % (新名, d)
    return d, json.loads((d / "预设图.json").read_text(encoding="utf-8"))


def _nodes(data):
    return [(m, n) for m in data["模块"] for n in m["节点"]]


def check_预设图落在家里且构成一致(workspace, reply):
    _, 预设 = _预设图(workspace)
    案件 = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    assert set(预设) == {"格式版本", "模块"}, "预设图顶层多了键：%s" % sorted(预设)
    assert [m["标题"] for m in 预设["模块"]] == [m["标题"] for m in 案件["模块"]], "模块该与案件图一致"
    assert len(_nodes(预设)) == len(_nodes(案件)), "节点数该与案件图一致：%d 对 %d" % (len(_nodes(预设)), len(_nodes(案件)))
    assert all(n["条目"] == [] for _, n in _nodes(预设)), "另存要剥掉全部条目"
    assert [n["id"] for _, n in _nodes(预设)] == [n["id"] for _, n in _nodes(案件)], "id 该原样带过去"


def check_标题去案件化(workspace, reply):
    _, 预设 = _预设图(workspace)
    hit = [n["标题"] for _, n in _nodes(预设) if 核心词 in n["标题"]]
    assert len(hit) == 1, "带「%s」的节点该恰有一个，实际 %s" % (核心词, hit)
    for 字 in 案件里的字:
        assert 字 not in hit[0], "预设图上的标题该去掉本案的「%s」，实际 %r" % (字, hit[0])
    案件 = json.loads((workspace / "图.json").read_text(encoding="utf-8"))
    原 = [n["标题"] for _, n in _nodes(案件) if 核心词 in n["标题"]]
    assert 原 == ["乙家甲年乙月丙日南墙菜畦补种记录"], "案件图上律师写的标题一个字不动，实际 %s" % 原


def check_模板整份拷走(workspace, reply):
    d, _ = _预设图(workspace)
    有 = sorted(p.name for p in (d / "模板").iterdir()) if (d / "模板").is_dir() else []
    assert 有 == ["播种登记.docx", "施肥记录.docx"], "参考/模板/ 该整份拷进新预设图的 模板/，实际 %s" % 有


def check_案件图一字不动(workspace, reply):
    校验基线(workspace)


def check_回复里有新名字(workspace, reply):
    assert 新名 in reply, "回复里该说往后起手怎么选它：\n%s" % reply
