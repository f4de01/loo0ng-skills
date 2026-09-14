"""种子「逐节点回流」：合成小领域「菜园」上一个办到一半的案件工作区，加一份活图。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
律师侧逐节点回流在办案会话里发生（ADR-0019）：当前目录就是案件工作区，领域目录是律师本机的
活图，一句话确认之后才问一次归属。所以这里摆的就是一个正常的案件工作区，外加它指着的那份活图：

    <工作区>/              案件工作区（六格、图与两份视图、AGENTS.md 指针块指着活图）
    <活图家>/领域/菜园/     活图，由 sketch.py home 从 evals/领域/菜园/ 这份「出厂种子」拷出
    <工作区>/.活图基线.json 律师那一句之前活图的样子：路径、逐文件 sha256、模块数与节点数

活图家取环境变量 LOO0NG_HOME：跑器每次运行建一个临时的交给两侧 harness（ADR-0015 只生不存）。
没设这个变量时（--materialize、脚本层单测）落在工作区里的 .活图家/ 下，永远不碰律师真的 ~/.loo0ng。

领域用合成小领域「菜园」（4 模块 9 节点），整份起手，再摆出两个已生成未确认的节点：

    乙家甲年乙月丙日南墙菜畦补种记录   律师自加，领域图里没有 → 确认之后该问一次归属
    除草                             领域图带入的，领域图里已经有 → 一个字不问

工作区里没有任何案件内容：文书与审查报告都是合成的几行字，当事人一律写甲乙丙。
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "evals" / "共用"))
import 活图断言 as 助手  # noqa: E402  节点名与「指纹」只有一份，用例的断言与本回放读同一处
SETUP = REPO / "skills" / "engineering" / "setup-case" / "scripts" / "setup.py"
ENGINE = REPO / "skills" / "engineering" / "graph" / "scripts" / "graph.py"
SKETCH = REPO / "skills" / "engineering" / "domain" / "scripts" / "sketch.py"
种子根 = REPO / "evals" / "领域"          # 合成小领域「菜园」在这里，当出厂种子用
LIVE_HOME_ENV = "LOO0NG_HOME"             # 活图的「家」，与 sketch.py、跑器同一个名字
领域名 = 助手.领域名
基线名 = 助手.基线名                       # 点开头：用例的「没往工作区乱写」断言按惯例忽略它

自加 = 助手.自加                           # 领域图里没有，去案件化之后核心词是「补种」
自加所在模块 = 助手.自加所在模块
带入 = 助手.带入                           # 领域图带入的，id 与领域图一致

DOCS = {
    自加: "# %s\n\n甲年乙月丙日，乙家南墙一畦出苗不齐，补种苗四十株，浇定根水一次。\n" % 自加,
    带入: "# %s\n\n甲年乙月丁日除草一遍，畦沟杂草清净，未用除草剂。\n" % 带入,
}
报告模板 = ("# %s 第 1 版审查报告\n\n## 生成依据\n\n合成种子，无真实材料\n\n"
            "## 存疑点\n\n无\n\n## 待律师裁定\n\n无\n\n## 版式门禁\n\n未跑（合成种子不出 DOCX）\n\n"
            "## 时限\n\n规则见领域图；基准日：缺失\n")


def run(cmd, cwd):
    r = subprocess.run([sys.executable, *[str(c) for c in cmd]], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
        raise SystemExit(r.returncode)
    return r.stdout


def 活图(ws: pathlib.Path) -> pathlib.Path:
    """跑 sketch.py home 取活图路径：没有就从 evals/领域/菜园/ 整份拷一份，回显第一行是绝对路径。"""
    if not os.environ.get(LIVE_HOME_ENV, "").strip():
        os.environ[LIVE_HOME_ENV] = str(ws / ".活图家")
    out = run([SKETCH, "home", "--name", 领域名, "--seed-root", 种子根], ws)
    第一行 = out.splitlines()[0]
    return pathlib.Path(第一行.split("：", 1)[1].strip())


def 出一版(ws: pathlib.Path, live: pathlib.Path, 节点: str):
    目录 = ws / "文书" / 节点
    目录.mkdir(parents=True, exist_ok=True)
    (目录 / ("%s-v1.md" % 节点)).write_text(DOCS[节点], encoding="utf-8")
    (目录 / ("%s-v1-审查报告.md" % 节点)).write_text(报告模板 % 节点, encoding="utf-8")
    rel = "文书/%s/%s-v1.md" % (节点, 节点)
    run([ENGINE, "--domain", live, "generate", "--node", 节点, "--doc", rel, "--source", rel,
         "--review", "文书/%s/%s-v1-审查报告.md" % (节点, 节点)], ws)


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    live = 活图(ws)
    run([SETUP, "init", "--full", "--domain", live, "--workspace", ws], ws)
    # 律师自加的那个节点：id 由引擎生成，回流时原样带进活图（ADR-0019）。
    run([ENGINE, "--domain", live, "add-node", "--module", 自加所在模块, "--title", 自加], ws)
    出一版(ws, live, 自加)
    出一版(ws, live, 带入)

    domain = json.loads((live / "领域图.json").read_text(encoding="utf-8"))
    基线 = {
        "活图": live.as_posix(),
        "指纹": 助手.指纹(live),
        "模块数": len(domain["模块"]),
        "节点数": sum(len(m["节点"]) for m in domain["模块"]),
    }
    # 显式 open：Path.write_text 的 newline= 是 3.10 才有的，种子要跟着引擎跑在 3.9 上（#61）
    with open(ws / 基线名, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(基线, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
