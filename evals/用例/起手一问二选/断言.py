"""起手一问二选用例的断言：没起手、没建格、根上六件原封不动、回复列出两组并在问。签名 (workspace: Path, reply: str)。"""
import pathlib
import re

SEED_DIR = pathlib.Path(__file__).resolve().parents[2] / "种子" / "空目录"
六件 = ("债务人移交物品清单.txt", "甲法院破产案件管理人工作提示.md", "（格式）债权申报登记表.md",
      "本所自用-接管物品交接单空表.md", "未命名.txt", "管理人承诺书（已交法院）.md")


def _is_harness_noise(name):
    """harness 跑 python 时留下的缓存目录（__pycache__、.uv-cache、uv-cache 等），不算工作区产物。"""
    return name == "__pycache__" or name.startswith(".") or name.startswith("uv-")


def check_没有起手(workspace, reply):
    for name in ("图.json", "图视图.md", "图视图.json", "AGENTS.md", "CLAUDE.md", "归档索引.md"):
        assert not (workspace / name).exists(), "没答空图还是哪份预设图之前不该起手，却落了 %s" % name
    for rel in ("待归档", "材料", "参考", "文书"):
        assert not (workspace / rel).exists(), "没答之前不该建格，却建了 %s/" % rel


def check_根上六件原封不动(workspace, reply):
    names = sorted(p.name for p in workspace.iterdir() if not _is_harness_noise(p.name))
    assert names == sorted(六件), "根上该还是那六件，实际 %s" % names
    for name in 六件:
        assert (workspace / name).read_bytes() == (SEED_DIR / name).read_bytes(), "%s 的内容变了" % name


def check_回复列出两组(workspace, reply):
    assert "破产" in reply, "出厂那组的「破产」没列出来：\n%s" % reply
    assert "菜园" in reply, "个人那组的「菜园」没列出来（列表要分两组）：\n%s" % reply
    assert "空图" in reply, "空图这个选项没给：\n%s" % reply


def check_没报成已经起好了(workspace, reply):
    assert not re.search(r"已(经)?起手|起手完成|已建好|目录与图[：:]", reply), "没答就报成起好了：\n%s" % reply
