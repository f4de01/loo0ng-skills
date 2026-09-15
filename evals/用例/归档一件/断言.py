"""归档一件用例的断言：原件按原名到了材料、另两件仍在待归档、索引一行、图没动。签名 (workspace: Path, reply: str)。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
from 基线 import 校验基线  # noqa: E402

SEED = pathlib.Path(__file__).resolve().parents[2] / "种子" / "待归档" / "待归档"
搬的 = "地块记录.txt"
留的 = ("播种日志空表.md", "合作社种植要求.md")
根上允许 = {"AGENTS.md", "CLAUDE.md", "图.json", "图视图.json", "图视图.md", "归档索引.md", "待归档", "材料", "参考", "文书"}


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_原件按原名到了材料(workspace, reply):
    target = workspace / "材料" / 搬的
    assert target.is_file(), "材料/ 下没有 %s" % 搬的
    assert target.read_bytes() == (SEED / 搬的).read_bytes(), "搬过去的内容变了"
    assert sorted(p.name for p in (workspace / "材料").iterdir()) == [搬的], "材料/ 里多出了东西"


def check_另两件仍在待归档(workspace, reply):
    left = sorted(p.name for p in (workspace / "待归档").rglob("*") if not _is_harness_noise(p.name))
    assert left == sorted(留的), "待归档里该只剩另两件，实际 %s" % left
    for name in 留的:
        assert (workspace / "待归档" / name).read_bytes() == (SEED / name).read_bytes(), "%s 被动过" % name
    assert not list((workspace / "参考" / "指南").iterdir()), "参考/指南 不该有东西"
    assert sorted(p.name for p in (workspace / "参考" / "模板").iterdir()) == ["播种登记.docx", "施肥记录.docx"], \
        "参考/模板 里只该有起手拷进来的两件"


def check_归档索引恰一行(workspace, reply):
    索引 = workspace / "归档索引.md"
    assert 索引.is_file(), "归档要维护工作区根的 归档索引.md"
    行 = [l for l in 索引.read_text(encoding="utf-8").splitlines() if l.startswith("| 材料/") or l.startswith("| 参考/")]
    assert len(行) == 1 and ("材料/" + 搬的) in 行[0], "索引该恰有一行、指着 材料/%s：%s" % (搬的, 行)


def check_图没动(workspace, reply):
    校验基线(workspace)


def check_没写别的文件(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    多 = [n for n in names if n not in 根上允许]
    assert not 多, "工作区里多出了东西：%s" % 多
