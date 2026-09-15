"""路由用例共用的断言：ask-matt 那五条验收项，加本项目自己的几条（#33 验收，#19、#20 重定）。

五条的出处是 `docs/research/ask-matt-路由写法解析.md` §3.3（原文可直接当测试）；
第六条是 ADR-0005 的「只指向表里真存在的入口」；再加只读基线、五段按序、待拍板行（#19：路由第一行
先说哪几份文书黄色已清、还等确认）。每个路由用例各 import 这几条，再加自己那一段情形的断言。
签名与用例里的断言一样，(workspace: Path, reply: str)。

第 4 条（断言行为前先读对方 `SKILL.md`）在一次调用里只能验到回复里的注明那一半：
跑器拿到的只有最后一条回复，看不到追踪，「真的去读了」由人工实测与关票那一次覆盖。
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from 基线 import 校验基线  # noqa: E402

入口 = r"(?:setup-case|doit|ask-loo0ng)"
整串 = r"[/$]" + 入口


段名 = ("你在哪", "三问", "往下的路", "相近入口分界线", "下一句该打什么")
标题头 = r"^[ \t]*(?:#{1,6}[ \t]*|\*\*)"


def 找标题(文, 标题):
    return re.search(标题头 + re.escape(标题), 文, re.M)


def 段(reply: str, 标题: str) -> str:
    """取某一段的正文：从这一段的小标题到下一个小标题之前。

    两个 harness 的 Markdown 口味不同（`## 三问` 与 `**三问**` 都出现过），标题头两种都认；
    段与段的边界按下一个已知小标题算，不按井号，免得段里的编号列表把段切断。
    """
    m = 找标题(reply, 标题)
    if not m:
        return ""
    尾 = reply[m.end():]
    下一段 = None
    for 名 in 段名:
        if 名 == 标题:
            continue
        mm = 找标题(尾, 名)
        if mm and (下一段 is None or mm.start() < 下一段):
            下一段 = mm.start()
    return 尾 if 下一段 is None else 尾[:下一段]


def 第一行(reply: str) -> str:
    """回复里第一个非空行：SKILL.md 说它必须是待拍板行。"""
    for line in reply.splitlines():
        if line.strip():
            return line.strip()
    return ""


def 节点标题(workspace) -> list:
    图 = json.loads((pathlib.Path(workspace) / "图.json").read_text(encoding="utf-8"))
    return [n["标题"] for m in 图["模块"] for n in m["节点"]]


def 视图节点(workspace) -> list:
    p = pathlib.Path(workspace) / "图视图.json"
    # 路由只读：这份文件跑完必须还在。不在就是路由动了它，这里给一条读得懂的红，
    # 而不是让断言模块抛 FileNotFoundError（那看不出是谁删的）。
    assert p.is_file(), "跑完 图视图.json 不在了：路由只读，它不该删或改这份文件"
    return [n for m in json.loads(p.read_text(encoding="utf-8"))["模块"] for n in m["节点"]]


def 待拍板的(workspace) -> list:
    """引擎算出来的待拍板：已生成、未确认、高亮已清。路由第一行该点的就是它们。"""
    return [n["标题"] for n in 视图节点(workspace) if n["状态"] == "已生成" and n["高亮"] == "已清"]


# 1. 结尾点名该打什么，然后停，不自己开工。
def check_结尾点名然后停(workspace, reply):
    m = None
    for mm in re.finditer(标题头 + "下一句该打什么", reply, re.M):
        m = mm
    assert m, "回复里没有「下一句该打什么」这一段：\n%s" % reply
    尾 = reply[m.start():]
    assert re.search(整串, 尾), "最后一段里没有可原样打的整串：\n%s" % 尾
    多出来的 = [名 for 名 in 段名 if 名 != "下一句该打什么" and 找标题(reply[m.end():], 名)]
    assert not 多出来的, "「下一句该打什么」之后还有别的段（%s），没有停：\n%s" % ("、".join(多出来的), 尾)
    行 = [l for l in 尾.splitlines()[1:] if l.strip()]
    assert len(行) <= 8, "最后一段拖了 %d 行，点名之后该停：\n%s" % (len(行), 尾)


# 2. 给回的路线提到在哪要人拍板、要不要开新对话，不只是入口名单。
def check_路线含拍板点与新对话(workspace, reply):
    s = 段(reply, "往下的路")
    assert s.strip(), "回复里没有「往下的路」这一段：\n%s" % reply
    assert "拍板" in s, "「往下的路」里没说哪一步要律师拍板：\n%s" % s
    assert "新对话" in s, "「往下的路」里没说要不要开新对话：\n%s" % s
    assert re.search(整串, s), "「往下的路」里没有整串：\n%s" % s


# 3. 两个相近入口，说清用哪个、另一个为什么不对。
def check_相近入口分界线(workspace, reply):
    s = 段(reply, "相近入口分界线")
    assert s.strip(), "回复里没有「相近入口分界线」这一段：\n%s" % reply
    assert "还是" in s, "分界线要写成「X 还是 Y，取决于 Z」：\n%s" % s


# 4. 凡对另一个入口行为的断言，以那个入口自己的 SKILL.md 为准（回复里注明）。
def check_断言以对方SKILL为准(workspace, reply):
    assert "SKILL.md" in reply, "回复里没注明对入口行为的说法以对方 SKILL.md 为准：\n%s" % reply
    assert re.search(入口, reply), "回复里一个入口名都没有：\n%s" % reply


# 5. 你在答案里认出自己的处境，而不是最近似的通用场景。
def check_认出自己处境(workspace, reply):
    s = 段(reply, "你在哪")
    assert s.strip(), "回复里没有「你在哪」这一段：\n%s" % reply
    assert re.search(r"主线第\s*[1-5]\s*步|无事可做|终点|空图", s), \
        "「你在哪」没落到主线的某一步上：\n%s" % s
    标题 = 节点标题(workspace)
    if 标题:
        assert any(t in reply for t in 标题), \
            "回复里一个本案节点都没点名，答的是通用场景：\n%s" % reply
    else:
        assert re.search(r"空图|一个节点都|还没出过|(还没有|没有|尚无)节点|(图|模块)[^\n]{0,6}空", reply), \
            "空图起手时「你在哪」该说清图是空的：\n%s" % s


# 本项目自己加的一条（ADR-0005 B7）：只指向表里真存在的三个入口，不编、不带命名空间前缀。
def check_只指向表里的三个入口(workspace, reply):
    # 前面紧挨着字母、数字、点、斜杠、冒号的不算：那是路径里的一段（如 skills/in-progress/domain/…），不是打给谁的。
    for 前缀, 名 in re.findall(r"(?<![\w./\\:-])([/$])([A-Za-z][A-Za-z0-9:_-]*)", reply):
        if 前缀 == "$" and not re.fullmatch(入口, 名):
            raise AssertionError("`$%s` 不是表里的入口（`$` 打裸名，不带命名空间前缀）：\n%s" % (名, reply))
        if 前缀 == "/" and "loo0ng" in 名 and not re.fullmatch(入口, 名):
            raise AssertionError("`/%s` 不是表里的入口：\n%s" % (名, reply))


# 只读：跑完三份图文件一个字节都不变（ADR-0005；#33 验收）。判据由种子的回放写在工作区里。
def check_只读没写图(workspace, reply):
    校验基线(workspace)


# 段序：五段按这个顺序出现（SKILL.md「固定五段，段序不变」）。
def check_五段按序(workspace, reply):
    位置 = []
    for 名 in 段名:
        m = 找标题(reply, 名)
        assert m, "回复里没有「%s」这一段：\n%s" % (名, reply)
        位置.append((m.start(), 名))
    乱 = [名 for (a, 名), (b, _) in zip(位置, 位置[1:]) if a >= b]
    assert not 乱, "五段的顺序不对（%s 排到了后一段之后）：%s" % ("、".join(乱), [名 for _, 名 in sorted(位置)])


# 第一行是待拍板行（SKILL.md「回复长什么样」，#19）：黄色已清、还没确认的逐个点名；一个没有就说无。
def check_第一行是待拍板行(workspace, reply):
    行 = 第一行(reply)
    assert 行.startswith("待拍板") or re.match(r"[*#\s]*待拍板", 行), \
        "回复的第一行该是「待拍板：…」，实际是：%r" % 行
    该点的 = 待拍板的(workspace)
    for 标题 in 该点的:
        assert 标题 in 行, "「%s」黄色已清、还没确认，待拍板行该点它：%r" % (标题, 行)
    # 整串只要求第一个那一份（SKILL.md：「后面接一句……与第一个那一串」），多份时其余只点名。
    if 该点的:
        assert re.search(r"确认\s*(?:%s)" % "|".join(re.escape(t) for t in 该点的), 行), \
            "待拍板行该给出第一个那一串「确认 %s」：%r" % (该点的[0], 行)
    if not 该点的:
        assert re.search(r"待拍板[：:]\s*无", 行), "没有黄色已清的文书时该写「待拍板：无」：%r" % 行
    for n in 视图节点(workspace):
        if n["状态"] == "已生成" and n["高亮"] != "已清":
            assert n["标题"] not in 行, "「%s」黄色未清，不算待拍板，不该出现在第一行：%r" % (n["标题"], 行)
