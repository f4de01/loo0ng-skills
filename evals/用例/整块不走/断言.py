"""路由用例「整块不走」的断言：命中问 3、下一句是前方第一个、不适用的那块不再排进往下的路。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

前方第一 = "管理人工作计划"
不适用的 = ("和解协议", "裁定认可和解协议并终结破产程序的申请")


def check_命中问3(workspace, reply):
    assert re.search(r"命中问\s*3", reply), "没有待确认的、前方还有节点，该命中问 3：\n%s" % reply


def check_下一句是前方第一个(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 前方第一)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_不适用的那块不排进往下的路(workspace, reply):
    for 名 in ("往下的路", "下一句该打什么"):
        s = 段(reply, 名)
        for t in 不适用的:
            assert t not in s, "「%s」已不适用，「%s」里不该再排它：\n%s" % (t, 名, s)
    for t in 不适用的:
        assert not re.search(r"[/$]doit 出一版 ?%s" % re.escape(t), reply), "不该给出打不适用节点的整串：\n%s" % reply
