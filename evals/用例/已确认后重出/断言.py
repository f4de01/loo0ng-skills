"""路由用例「已确认后重出」的断言：重出的那份回到待确认、上一完成退回另一份、下一句是确认重出的那版。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

重出的 = "管理人承诺书及团队人员"
仍已确认的 = "管理人印章备案报告"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "重出的那份黄色已清、等确认，该命中问 1：\n%s" % reply


def check_当前节点是重出的那份(workspace, reply):
    s = 段(reply, "三问")
    当前 = [l for l in s.splitlines() if "当前节点" in l]
    assert 当前 and 重出的 in 当前[0], "当前节点该是重出后等确认的「%s」：%s" % (重出的, 当前)


def check_上一完成退回印章备案(workspace, reply):
    s = 段(reply, "三问")
    上一 = [l for l in s.splitlines() if "上一完成" in l]
    assert 上一 and 仍已确认的 in 上一[0], "重出过的不算完成，上一完成该退回「%s」：%s" % (仍已确认的, 上一)
    assert 重出的 not in 上一[0], "「%s」重出后已不是已确认，不该算上一完成：%s" % (重出的, 上一)


def check_下一句是确认重出的那版(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 重出的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_分界线说清出一版还是重出(workspace, reply):
    s = 段(reply, "相近入口分界线")
    assert "重出" in s or "出一版" in s, "相近入口分界线该说清出一版还是重出：\n%s" % s
