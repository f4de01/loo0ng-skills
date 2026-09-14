"""路由用例「已确认后重出」的断言：重出过的节点不算完成，上一完成退回上一个。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

重出的 = "管理人承诺书及团队人员"
上一完成 = "管理人印章备案报告"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "重出的那一版在等拍板，该命中问 1：\n%s" % reply


def check_当前节点是重出的那一份(workspace, reply):
    行 = [l for l in 段(reply, "三问").splitlines() if "当前节点" in l]
    assert 行, "「三问」里没有当前节点这一行：\n%s" % reply
    assert 重出的 in 行[0], "重出之后它回到已生成、等拍板：%s" % 行[0]


def check_上一完成不再是重出过的那个(workspace, reply):
    行 = [l for l in 段(reply, "三问").splitlines() if "上一完成" in l]
    assert 行, "「三问」里没有上一完成这一行：\n%s" % reply
    assert 上一完成 in 行[0], "重出过的节点现在是已生成、不算完成，上一完成该退回「%s」：%s" % (上一完成, 行[0])
    assert 重出的 not in 行[0], "重出过的节点不该再算上一完成：%s" % 行[0]


def check_下一句是确认重出的那一版(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 重出的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_分界线说清了重出(workspace, reply):
    s = 段(reply, "相近入口分界线")
    assert "重出" in s or "再出一版" in s, "这一步的相近入口分界线该说清出一版还是重出：\n%s" % s
