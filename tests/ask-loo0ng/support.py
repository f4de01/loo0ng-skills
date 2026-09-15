"""tests/ask-loo0ng 的公用件：路由没有脚本，被断的是它的正文，所以公用的是切正文的那几刀。

同一个形状两份测试都要用：找到一个标题，扫到下一个标题为止，把那一段（或那一段里的表）交出去。
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
# 路由住哪个桶不写死，按名当场解析（evals/共用/桶.py，与 eval 那一侧同一处）。
sys.path.insert(0, str(REPO / "evals" / "共用"))
from 桶 import skill目录 as 件, 全部skill名  # noqa: E402

SKILL_DIR = 件("ask-loo0ng")
SKILL = SKILL_DIR / "SKILL.md"
YAML = SKILL_DIR / "agents" / "openai.yaml"
下一任务 = SKILL_DIR / "references" / "下一任务.md"


def 正文():
    return SKILL.read_text(encoding="utf-8")


def 一节(标题: str, 到下一个: str = "## "):
    """某个标题那一节。默认扫到下一个二级标题为止（子节留在里面）。

    围栏代码块里的 `##` 是样例回复的小标题，不是正文的标题，扫的时候要跳过去。
    """
    行 = 正文().splitlines()
    assert 标题 in 行, "正文里没有「%s」这个标题" % 标题
    出 = []
    围栏 = False
    for line in 行[行.index(标题) + 1:]:
        if line.startswith("```"):
            围栏 = not 围栏
        elif not 围栏 and line.startswith(到下一个):
            break
        出.append(line)
    return "\n".join(出)


def 表里的行(标题: str):
    """某个标题下第一张表的行：第一列反引号里的名字 -> 第二列。到下一个标题（任何级别）为止。"""
    rows = {}
    for line in 一节(标题, 到下一个="#").splitlines():
        m = re.match(r"^\|\s*`([a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows
