"""七个路由种子共用的回放动作（#33、#92）。

每个种子都是「按真实的破产领域目录起手，再逐条调引擎摆出一个状态」，只有那几条命令不同；
把重复的部分收在这里，种子的 `回放.py` 只剩它自己那几步，读起来就是那个状态本身。
起手与写图仍走真的 CLI（skill "setup-case" 与 skill "graph"），
引擎一改、起手一改，用这些种子的用例立刻红。

文书与审查报告都是合成的几行字，当事人与法院一律写甲乙丙，不含隐私检查器五类正则能命中的值。
"""
import os
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
SETUP = REPO / "skills" / "engineering" / "setup-case" / "scripts" / "setup.py"
ENGINE = REPO / "skills" / "engineering" / "graph" / "scripts" / "graph.py"
SKETCH = REPO / "skills" / "engineering" / "domain" / "scripts" / "sketch.py"
LIVE_HOME_ENV = "LOO0NG_HOME"  # 活图的「家」，与 sketch.py、跑器同一个名字
# 默认直接给包内的出厂种子，不走活图（ADR-0019 的 sketch.py home）：这些种子要的是一个确定的状态，
# 拷一份活图只是多一层间接。它同时是「0.1.0 起手、没迁移过的工作区」那个形状：指针块指着种子、
# 仍读得到，路由照常答（#92 第 2 条）。要一份真的活图的种子调 用活图() 换掉它。
出厂种子 = REPO / "skills" / "engineering" / "domain" / "assets" / "破产"
_领域目录 = [出厂种子]


def 领域目录() -> pathlib.Path:
    """起手与引擎这一轮用哪个领域目录。默认出厂种子，调过 用活图() 就是那份活图。"""
    return _领域目录[0]


def 用活图(ws, 领域名="破产") -> pathlib.Path:
    """跑 sketch.py home 取活图路径，往后的 起手() 与 引擎() 都指它（ADR-0019、#92）。

    活图家取环境变量 LOO0NG_HOME：跑器每次运行建一个临时的交给两侧 harness（ADR-0015 只生不存）。
    没设这个变量时（--materialize、脚本层单测）落在工作区里的 .活图家/ 下，永远不碰律师真的
    ~/.loo0ng。回显第一行是 `活图：<绝对路径>`。
    """
    if not os.environ.get(LIVE_HOME_ENV, "").strip():
        os.environ[LIVE_HOME_ENV] = str(pathlib.Path(ws) / ".活图家")
    第一行 = run(ws, SKETCH, "home", "--name", 领域名).splitlines()[0]
    _领域目录[0] = pathlib.Path(第一行.split("：", 1)[1].strip())
    return _领域目录[0]


def run(ws, *args):
    r = subprocess.run([sys.executable, *[str(a) for a in args]], cwd=str(ws),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
        raise SystemExit(r.returncode)
    return r.stdout


_上次写图 = [0.0]


def 隔开一秒():
    """两次写图之间等到整秒跳一格：条目时间只到秒，同一秒里落两条就分不出先后，
    「上一完成 = 确认最晚的」这条断言会变成掷硬币（#33 的用例「跳着走」上真的撞上过）。"""
    while int(time.time()) <= int(_上次写图[0]):
        time.sleep(0.05)


def 引擎(ws, *args):
    隔开一秒()
    out = run(ws, ENGINE, "--domain", 领域目录(), *args)
    _上次写图[0] = time.time()
    return out


def 起手(ws, 方式="--empty"):
    """方式：--empty 空图起手，--full 整份领域图起手。"""
    return run(ws, SETUP, "init", 方式, "--domain", 领域目录(), "--workspace", ws)


def 出一版(ws, 节点, 第几版=1):
    """写一份合成的文书与审查报告，再经引擎追加一条生成条目（惰性带入节点）。"""
    目录 = pathlib.Path(ws) / "文书" / 节点
    目录.mkdir(parents=True, exist_ok=True)
    稿 = 目录 / ("%s-v%d.md" % (节点, 第几版))
    报告 = 目录 / ("%s-v%d-审查报告.md" % (节点, 第几版))
    稿.write_text("# %s\n\n甲公司破产清算案，本件为第 %d 版合成稿，只求形状对。\n" % (节点, 第几版),
                  encoding="utf-8")
    报告.write_text(
        "# %s 第 %d 版审查报告\n\n## 生成依据\n\n合成种子，无真实材料\n\n"
        "## 存疑点\n\n无\n\n## 待律师裁定\n\n无\n\n## 版式门禁\n\n未跑（合成种子不出 DOCX）\n\n"
        "## 时限\n\n规则见领域图；基准日：缺失\n" % (节点, 第几版), encoding="utf-8")
    rel = "文书/%s/%s" % (节点, 稿.name)
    return 引擎(ws, "generate", "--node", 节点, "--doc", rel, "--source", rel,
                "--review", "文书/%s/%s" % (节点, 报告.name))


def 领域图引擎(ws, *args):
    """改领域图本身（--kind domain）：只有种子「活图多一件」用它，把活图改成与出厂种子不一样。

    走的是同一个引擎，领域图是它的另一种 --kind；活图不在工作区里，所以 --graph 要给绝对路径。
    """
    return run(ws, ENGINE, "--graph", 领域目录() / "领域图.json", "--kind", "domain", *args)


def 确认(ws, 节点, 原话):
    return 引擎(ws, "confirm", "--node", 节点, "--words", 原话)


def 办完(ws, 节点, 原话, 第几版=1):
    出一版(ws, 节点, 第几版)
    确认(ws, 节点, 原话)
