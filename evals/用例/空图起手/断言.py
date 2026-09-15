"""路由用例「空图起手」的断言：空图上三问怎么答、命中哪一问、不编预设图里的节点。签名 (workspace: Path, reply: str)。"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 路由断言 import 段, 找标题, 整串  # noqa: E402
from 路由断言 import (  # noqa: E402,F401
    check_相近入口分界线, check_断言以对方SKILL为准, check_认出自己处境,
    check_只指向表里的三个入口, check_只读没写图, check_五段按序, check_第一行是待拍板行)

预设图里才有的 = ("管理人承诺书", "印章备案", "债权表")


def check_命中问4(workspace, reply):
    assert re.search(r"命中问\s*4", reply), \
        "空图上问 1 至 3 都不成立（一个节点都没有、前方为空），该命中问 4：\n%s" % reply


def check_没有待确认也没有上一完成(workspace, reply):
    s = 段(reply, "三问")
    assert s.strip(), "回复里没有「三问」这一段：\n%s" % reply
    当前 = [l for l in s.splitlines() if "当前节点" in l]
    上一 = [l for l in s.splitlines() if "上一完成" in l]
    assert 当前 and re.search(r"没有|无", 当前[0]), "空图上该答没有待确认的文书：%s" % 当前
    assert 上一 and re.search(r"没有|还没|无", 上一[0]), "空图上该答还没有完成的节点：%s" % 上一


def check_不提预设图里的节点(workspace, reply):
    """图自足（ADR-0023）：视图里没有的节点本案就是没有，路由不去别处比对、不提别处有什么。"""
    for t in 预设图里才有的:
        assert t not in reply, "空图上不该冒出预设图里的「%s」（图自足，不去别处找）：\n%s" % (t, reply)


没有下一句 = r"没有[^\n]{0,12}下一句|无事可做|没有可打的|没有可(直接)?执行"


说一句就到 = r"说一句|说这句|直接说|整理进来|归一下|加一个(节点|模块)|存成预设图|哪些槽"


def check_结尾点名或明说没有下一句(workspace, reply):
    """空图上「下一句该打什么」有三种合法形状，都收；这一条只守「给了律师能用的东西」与「给完就停」。

    正文给了三种：整串（`doit 出一版 <律师自己定的标题>`）；无事可做时明说没有下一句（第 6 条）；
    第一步是「说一句话就到」的那四件时写律师要说的话、**不写 `/名`**（第 4 条，空图上要加节点正是那一档）。
    两侧实测三种都出现过，所以不拿其中任何一种当唯一判据。

    第 6 条那半句「并说明要重出仍是打 `doit`」这里不断：它写给问 4 的另一种情形（节点都已确认或不适用），
    空图上一份文书都没出过，重出无从谈起，两侧各有一半的回合据此略去它。这是正文把问 4 两种情形写在
    一句里的后果，留给 ask-loo0ng 的票，不在这里拿模型的判断当红。
    """
    m = 找标题(reply, "下一句该打什么")
    assert m, "回复里没有「下一句该打什么」这一段：\n%s" % reply
    尾 = reply[m.start():]
    assert re.search(整串, 尾) or re.search(没有下一句, 尾) or re.search(说一句就到, 尾), \
        "最后一段既没给整串、没明说没有下一句，也没给一句说了就到的话：\n%s" % 尾
    行 = [l for l in 尾.splitlines()[1:] if l.strip()]
    assert len(行) <= 8, "最后一段拖了 %d 行，点名之后该停：\n%s" % (len(行), 尾)


def check_往下的路或说无事可做(workspace, reply):
    """共用那条要求「往下的路」里有拍板点、新对话与整串；空图上没有步骤可排，正文允许直说无事可做。

    所以这一条替下共用的 check_路线含拍板点与新对话：给了步骤就按共用那三样查，没给就必须说清为什么没有。
    """
    s = 段(reply, "往下的路")
    assert s.strip(), "回复里没有「往下的路」这一段：\n%s" % reply
    # 「拍板」加「新对话」两行齐了就算排成了步骤，不另要整串：正文第 4 条写明，这一步指向
    # 「说一句话就到」的那四件时，那一行写律师要说的话、不写 /名（空图上要加节点，正是那一档）。
    完整步骤 = "拍板" in s and "新对话" in s
    说清没步骤 = re.search(
        r"无事可做|没有[^\n]{0,10}(下一句|下一步|步骤|可排|可办|可做|节点)|空图|一个节点都|还没有节点", s)
    assert 完整步骤 or 说清没步骤, \
        "空图上要么按正文排成步骤（每步整串加拍板、新对话两行），要么说清没有步骤可排：\n%s" % s
