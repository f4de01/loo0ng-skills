"""路由用例「问了图里没有的事」的断言：说对不上、不编入口、照常答三问、下一句是律师问的那件事。签名 (workspace: Path, reply: str)。"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

待确认的 = "管理人印章备案报告"


def check_说了对不上(workspace, reply):
    assert re.search(r"对不上|没有(这个|对应)?节点|(案件图|视图|图里)[^\n]{0,12}没有", reply), \
        "图里对不上的事该明说对不上，不猜：\n%s" % reply


def check_指向办节点入口(workspace, reply):
    assert "doit" in reply, "该指向 doit（它按律师说的标题把节点建进图再出件）：\n%s" % reply


def check_照常答了三问(workspace, reply):
    s = 段(reply, "三问")
    assert s.strip(), "对不上也要照常答三问：\n%s" % reply
    assert 待确认的 in s, "当前节点该是种子里那份待确认的「%s」：\n%s" % (待确认的, s)
    assert re.search(r"命中问\s*2", reply), "那份文书里还有黄等律师动手，该命中问 2：\n%s" % reply


def check_没往图里新建节点(workspace, reply):
    图 = json.loads((pathlib.Path(workspace) / "图.json").read_text(encoding="utf-8"))
    标题 = [n["标题"] for m in 图["模块"] for n in m["节点"]]
    assert "情况说明" not in "".join(标题), "路由不写图、不新建节点：%s" % [t for t in 标题 if "情况说明" in t]


def check_下一句是律师问的那件事(workspace, reply):
    """对不上的那件事排在往下的路第一步，下一句就是它那一串（SKILL.md「图里对不上的事」）。

    标题用律师说的那几个字，具体几个字由模型定（他说的是「给法院写一份情况说明」），
    所以整串按形状断言：前缀 + 入口 + 出一版 + 含「情况说明」的标题。
    """
    for 前缀 in ("/", r"\$"):
        整串 = 前缀 + r"doit 出一版 [^\n`]*情况说明"
        assert re.search(整串, reply), "回复里没有可原样打的整串「%s出一版 …情况说明」：\n%s" % (
            前缀.replace("\\", ""), reply)
