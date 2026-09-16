"""按 skill 名解析它住哪个桶：全仓库唯一一处写「桶」这个字的地方。

eval 的回放与几条用例断言要拿随包脚本的绝对路径（起手 CLI、图引擎、归档、填模板、出厂预设图），
路由的测试要拿它那份正文。桶是会变的：一件 skill 从 `in-progress/` 毕业回 `engineering/` 或
`productivity/` 时，写死桶名的地方要一处处跟着改，漏一处就是一条指着空气的路径。

所以谁都不写桶名，只说 skill 的名字，桶当场由 `skills/` 下的实际目录解析。
解析不到、或在两个桶里都有，都当场报死而不是回一个不存在的路径：那正是搬桶漏了一步的样子。
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"


def skill目录(名: str) -> pathlib.Path:
    """`skills/<桶>/<名>/`，按 `SKILL.md` 在不在认。找不到或找到多个都抛 SystemExit。"""
    命中 = sorted(p.parent for p in SKILLS.glob("*/%s/SKILL.md" % 名))
    if not 命中:
        raise SystemExit("skills/ 下没有名叫「%s」的 skill（搬桶漏了一步？）" % 名)
    if len(命中) > 1:
        raise SystemExit("skill「%s」同时住在 %s" % (名, "、".join(p.parent.name for p in 命中)))
    return 命中[0]


def 全部skill名():
    """`skills/` 下所有 skill 的名字，不论住哪个桶。用来断「一件都没漏」。"""
    return sorted(p.parent.name for p in SKILLS.glob("*/*/SKILL.md"))


def 脚本(名: str, 文件名: str) -> pathlib.Path:
    """某件 skill 随包脚本的绝对路径：`skills/<桶>/<名>/scripts/<文件名>`。"""
    return skill目录(名) / "scripts" / 文件名


def 相对仓库(路径: pathlib.Path) -> str:
    """仓库内相对路径，正斜杠。写进断言消息、或拿去在别的文本里找它时用。"""
    return pathlib.Path(路径).resolve().relative_to(REPO).as_posix()
