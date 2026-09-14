"""路由用例「跳着走」的断言：命中问 3，顺着最近动过的那一块做完，不把律师拽回前面。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序)

同模块最早的 = "债权申报与审核流程规则"
回头补空才轮到的 = "管理人工作计划"
上一完成 = "债权表"


def check_命中问3(workspace, reply):
    assert re.search(r"命中问\s*3", reply), \
        "没有待确认、案件图里也没有未生成的，该命中问 3（顺着最近动过的那一块做完）：\n%s" % reply


def check_下一句是同一块里最早的那个(workspace, reply):
    for 前缀 in ("/", "$"):
        串 = "%sdoit 出一版 %s" % (前缀, 同模块最早的)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)


def check_没把律师拽回前面那一块(workspace, reply):
    尾 = reply[reply.rfind("下一句该打什么"):]
    assert 回头补空才轮到的 not in 尾, \
        "问 3 排在问 4 前面：跳着走时顺着这一块做完，不回头补「%s」：\n%s" % (回头补空才轮到的, 尾)


def check_上一完成是确认最晚的那个(workspace, reply):
    行 = [l for l in 段(reply, "三问").splitlines() if "上一完成" in l]
    assert 行, "「三问」里没有上一完成这一行：\n%s" % reply
    assert 上一完成 in 行[0], "两个节点都已确认，上一完成该是确认最晚的「%s」：%s" % (上一完成, 行[0])
