"""指针指着种子的工作区里走完一次确认：确认照落，回流被引擎拒，种子一个字节不变。签名 (workspace, reply)。"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 活图断言 as 助手  # noqa: E402  节点名与「指纹」的读法与种子共用一处

基线名 = ".种子基线.json"
自加, 核心 = 助手.自加, 助手.自加的核心词


def 基线(workspace) -> dict:
    p = pathlib.Path(workspace) / 基线名
    assert p.is_file(), "种子没写下 %s，这几条断言无从比对" % 基线名
    return json.loads(p.read_text(encoding="utf-8"))


def check_确认照样落了(workspace, reply):
    """拒的只是往领域图写。确认是案件图上的事，一个字不受影响，不然这条守门就把办案挡住了。"""
    助手.校验确认落了(workspace, 自加)


def check_种子逐字不变(workspace, reply):
    """本票那条验收：走完一次确认之后，指针指着的那份出厂种子一个字节没动（ADR-0020）。"""
    base = 基线(workspace)
    现在 = 助手.指纹(pathlib.Path(base["种子"]))
    assert 现在 == base["指纹"], \
        "出厂种子被写了：律师累计的东西写进这里，下一次 skill 包升级就整个没了。\n回流前 %s\n现在   %s" \
        % (base["指纹"], 现在)


def check_提案照样回显(workspace, reply):
    """被拒不等于不问：归属提案照样回显给律师（票里明写），只是没写进去。

    去案件化后的标题多半是案件里那个标题的真子串，所以先把原标题的所有出现抠掉，
    剩下的文字里还得有核心词，才算真的回显过提案，而不是只把案件里的原标题读了一遍。
    """
    assert 核心 in reply, "回复里没提那个节点：\n%s" % reply[:400]
    assert 核心 in reply.replace(自加, ""), \
        "回复里只把案件里的原标题读了一遍，没回显去案件化后的归属提案：\n%s" % reply[:400]


def check_照实转告了为什么写不进去(workspace, reply):
    """引擎拒了就照实转告，别绕（doit 正文）。律师要能从这段话里看出下一步。"""
    assert "活图" in reply, "没告诉律师领域图该住哪儿（活图）：\n%s" % reply[:600]
    assert any(片 in reply for 片 in ("AGENTS.md", "领域目录", "指针")), \
        "没告诉律师要换的是工作区里「领域目录」那一行：\n%s" % reply[:600]


def check_没替律师改那一行(workspace, reply):
    """换指针是律师的事，agent 不替他改：那一行一动，这个工作区往后指向哪儿就没人说得清了。"""
    行 = [l for l in (pathlib.Path(workspace) / "AGENTS.md").read_text(encoding="utf-8").splitlines()
          if l.startswith("- 领域目录：")]
    assert 行 == [基线(workspace)["指针行"]], \
        "工作区 AGENTS.md 里「领域目录」那一行被改了：%s" % 行


def check_没在工作区里另造一份领域图(workspace, reply):
    """被拒之后绕道：在工作区里自己开一份领域图写进去，等于把这条守门原地废掉。"""
    种子 = pathlib.Path(基线(workspace)["种子"]) / "领域图.json"
    别处 = [p for p in pathlib.Path(workspace).rglob("领域图.json") if p.resolve() != 种子.resolve()]
    assert not 别处, "工作区里多出了领域图：%s" % [p.as_posix() for p in 别处]
