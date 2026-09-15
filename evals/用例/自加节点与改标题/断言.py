"""路由用例「自加节点与改标题」的断言：用现在的标题、时限跟着节点走、自加的节点是前方第一个。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_结尾点名然后停, check_路线含拍板点与新对话, check_相近入口分界线,
    check_断言以对方SKILL为准, check_认出自己处境, check_只指向表里的三个入口,
    check_只读没写图, check_五段按序, check_第一行是待拍板行)

现在的标题 = "承诺书"
旧标题 = "管理人承诺书及团队人员"
自加的 = "补充材料说明"
时限 = "自收到指定管理人决定书之日起 3 日内组建工作团队进驻债务人企业，并将团队情况向法院报备（手册，法院要求）"


def check_命中问1(workspace, reply):
    assert re.search(r"命中问\s*1", reply), "「承诺书」黄色已清、等确认，该命中问 1：\n%s" % reply


def check_下一句用现在的标题(workspace, reply):
    """整串用现在的标题。

    旧标题只在「当成节点名用」时才算错：它在视图里还以别的身份出现（空白模板文件名
    `1-1.管理人承诺书及团队人员（管理人选出后）.docx`、文书路径 `文书/接受指定与报备/管理人承诺书及团队人员/`），
    路由照读那两样是允许的，所以不能拿裸子串当判据。
    """
    for 前缀 in ("/", "$"):
        串 = "%sdoit 确认 %s" % (前缀, 现在的标题)
        assert 串 in reply, "回复里没有可原样打的整串「%s」：\n%s" % (串, reply)
    误用 = re.search(r"[/$]doit\s+(?:确认|出一版|重出)\s*" + re.escape(旧标题), reply)
    assert not 误用, "整串里把节点叫成了改之前的「%s」：\n%s" % (旧标题, reply)


def check_时限跟着节点走(workspace, reply):
    assert 时限 in reply, "改标题不动时限，往下的路里该原样附上那句：\n%s" % reply


def check_自加的节点是前方第一个(workspace, reply):
    s = 段(reply, "往下的路")
    assert re.search(r"出一版 ?%s" % 自加的, s), "律师自加的「%s」紧跟承诺书之后、是前方第一个，往下的路该排它：\n%s" % (自加的, s)
