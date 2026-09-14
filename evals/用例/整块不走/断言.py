"""路由用例「整块不走」的断言：宣告不适用的整块不再被提，下一任务落回领域图。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

要生成的 = "管理人工作计划"
不走的节点 = ("和解协议", "裁定认可和解协议并终结破产程序的申请")


def check_命中问4(workspace, reply):
    assert re.search(r"命中问\s*4", reply), \
        "最近动过的模块整个不适用、没有剩下的节点，该命中问 4：\n%s" % reply


def check_下一句是领域图里最早没做的(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 要生成的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_不把不适用的节点排进往下的路(workspace, reply):
    """不适用是终态，路由不再把它当任务。

    三问里作为背景提一句「自行和解那两个节点已不适用」是可以的（律师问的就是现在到哪了），
    真正不该发生的是把它排进往下的路、或给出打它的整串。
    """
    for 段名 in ("往下的路", "下一句该打什么"):
        s = 段(reply, 段名)
        for 节点 in 不走的节点:
            assert 节点 not in s, "「%s」已宣告不适用，「%s」里不该再排它：\n%s" % (节点, 段名, s)
    for 串 in re.findall(r"[/$]doit[^\n`]*", reply):
        assert "和解" not in 串, "不该给出打不适用节点的整串：%s" % 串
