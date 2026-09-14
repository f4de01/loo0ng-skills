"""种子「指针指着种子」：指针块还指着出厂种子的 0.1.0 工作区（#99，ADR-0020）。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）

摆的是 #90 留下的那个形状：0.1.0 起手的工作区，`AGENTS.md` 里「领域目录」那一行指着
skill 包内的**出厂种子**而不是包外的活图（本版不迁移，要改就手改那一行）。在这样的工作区里
走一遍律师侧逐节点回流，写的就会是随包分发的那份文件：下一次 skill 包升级整个换掉，
律师累计的东西静默消失。ADR-0020 的裁定是：引擎无条件拒，提案照样回显，告诉律师怎么换。

    <工作区>/                              案件工作区（六格、图与两份视图、AGENTS.md 指着下面那份种子）
    <工作区>/.假包/loo0ng-domain/assets/菜园/  **假的**出厂种子，指针块指着它
    <工作区>/.种子基线.json                  律师那一句之前那份种子的样子：路径与逐文件 sha256

**为什么是假包。** 判据有两条取或（见 graph.py 的 in_package）：按脚本位置算出的真 assets/，
或者目录名摆成 `<...>/loo0ng-domain/assets/<领域名>`。这里用第二条造一份形状一样的假包，
所以引擎照拒不误，而仓库里真的 `skills/productivity/loo0ng-domain/assets/` 一个字节都不会被这条用例碰到；
拿真包跑就是拿开发者的工作树赌一次规则，规则坏了它会被写脏。真包落在判据 ① 射程里这件事
由脚本层单测 tests/loo0ng-graph/test_package_guard.py 单独钉住，两条合起来才等于票里那句
「包内 assets/<领域>/领域图.json 字节不变」。假包放在工作区里的点开头目录下，与种子
「逐节点回流」的 .活图家/ 同一个惯例：点开头，用例的「没往工作区乱写」断言按惯例忽略它。

这个工作区**没有活图**：0.1.0 的形状就是从没跑过 sketch.py home。所以模型被拒之后无处可写，
只能照实转告，这正是要测的。领域用合成小领域「菜园」，整份起手，再摆出一个已生成未确认、
且领域图里没有的节点（律师自加的那份补种记录），确认之后本该问一次归属。

工作区里没有任何案件内容：文书与审查报告都是合成的几行字，当事人一律写甲乙丙。
"""
import json
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "evals" / "共用"))
import 活图断言 as 助手  # noqa: E402  节点名与「指纹」只有一份，用例的断言与本回放读同一处

SETUP = REPO / "skills" / "productivity" / "loo0ng-setup-case" / "scripts" / "setup.py"
ENGINE = REPO / "skills" / "productivity" / "loo0ng-graph" / "scripts" / "graph.py"
出厂种子源 = REPO / "evals" / "领域" / 助手.领域名      # 合成小领域「菜园」，当出厂种子的内容用

假包目录名 = ".假包"                                   # 点开头：不算「往工作区乱写」
基线名 = ".种子基线.json"
领域名 = 助手.领域名
自加 = 助手.自加                                      # 领域图里没有它 → 确认之后本该问一次归属
自加所在模块 = 助手.自加所在模块

DOC = "# %s\n\n甲年乙月丙日，乙家南墙一畦出苗不齐，补种苗四十株，浇定根水一次。\n" % 自加
报告 = ("# %s 第 1 版审查报告\n\n## 生成依据\n\n合成种子，无真实材料\n\n## 存疑点\n\n无\n\n"
        "## 待律师裁定\n\n无\n\n## 版式门禁\n\n未跑（合成种子不出 DOCX）\n\n"
        "## 时限\n\n规则见领域图；基准日：缺失\n") % 自加


def run(cmd, cwd):
    r = subprocess.run([sys.executable, *[str(c) for c in cmd]], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
        raise SystemExit(r.returncode)
    return r.stdout


def 摆一份假种子(ws: pathlib.Path) -> pathlib.Path:
    """判据 ②：目录名摆成 <...>/loo0ng-domain/assets/<领域名>，引擎就认它是包内的出厂种子。"""
    d = ws / 假包目录名 / "loo0ng-domain" / "assets" / 领域名
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(出厂种子源), str(d))
    return d


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    种子 = 摆一份假种子(ws)
    # 起手把这条路径原样记进 AGENTS.md：0.1.0 那一版就是这么落下的（setup.py 会顺带报一句，
    # 只报不拒，ADR-0020 把「拒」放在写图那一刻，起手那一头一个字没动）。
    run([SETUP, "init", "--full", "--domain", 种子, "--workspace", ws], ws)
    # 律师自加的那个节点：领域图里没有，id 由引擎生成。
    run([ENGINE, "--domain", 种子, "add-node", "--module", 自加所在模块, "--title", 自加], ws)
    目录 = ws / "文书" / 自加
    目录.mkdir(parents=True, exist_ok=True)
    (目录 / ("%s-v1.md" % 自加)).write_text(DOC, encoding="utf-8")
    (目录 / ("%s-v1-审查报告.md" % 自加)).write_text(报告, encoding="utf-8")
    rel = "文书/%s/%s-v1.md" % (自加, 自加)
    run([ENGINE, "--domain", 种子, "generate", "--node", 自加, "--doc", rel, "--source", rel,
         "--review", "文书/%s/%s-v1-审查报告.md" % (自加, 自加)], ws)

    基线 = {"种子": 种子.as_posix(), "指纹": 助手.指纹(种子),
            "指针行": [l for l in (ws / "AGENTS.md").read_text(encoding="utf-8").splitlines()
                       if l.startswith("- 领域目录：")][0]}
    # 显式 open：Path.write_text 的 newline= 是 3.10 才有的，种子要跟着引擎跑在 3.9 上（#61）
    with open(ws / 基线名, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(基线, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
