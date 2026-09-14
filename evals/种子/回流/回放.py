"""种子「回流」：一份律师自己长出过两个节点的案件工作区，加一份破产领域的活图。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
回流只在开发会话发生（ADR-0012）：当前目录是本仓库、开发者一句话给出案件工作区的路径，
写的是开发者本机的**活图**（ADR-0020）。跑器把 cwd 设在临时工作区，所以这里摆的是：

    <工作区>/案件/           案件工作区（先照「在办中」回放一遍，再加两个律师自加节点）
    <活图家>/领域/破产/       活图，由 sketch.py home 从包内 assets/破产/ 这份出厂种子拷出
    <工作区>/.活图基线.json   回流之前的样子：案件图的 sha256、活图路径、逐文件 sha256、模块数与节点数

活图家取环境变量 LOO0NG_HOME：跑器每次运行建一个临时的交给两侧 harness（ADR-0015 只生不存）。
没设这个变量时（--materialize、脚本层单测）落在工作区里的 .活图家/ 下，永远不碰开发者真的 ~/.loo0ng；
取路径这一步用 evals/共用/回放助手.py 的 用活图()，与七个路由种子同一份写法。
活图而不是工作区里摆一份副本：真实那条路的第 1 步就是跑 home 取路径（`references/回流.md`），
提示词里不给路径，这一步得由模型自己走（#105）。

两个自加节点都挂在领域图已有的模块「接管与调查」下，标题带着本案的当事人与日期：
    乙公司甲年乙月丙日厂区接管现场情况说明   一版生成 + 律师确认 → 回流候选
    乙公司食堂承包合同解除请示               只生成没拍板 → 不是候选（判据 a，ADR-0012）
工作区里没有任何案件内容：文书与审查报告都是合成的几行字，当事人与法院一律写甲乙丙。
"""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "evals" / "共用"))
import 活图断言 as 助手      # noqa: E402  「指纹」与基线文件名只有一份，用例的断言与本回放读同一处
import 回放助手              # noqa: E402  取活图路径这一步与七个路由种子共用一份写法

ENGINE = REPO / "skills" / "productivity" / "loo0ng-graph" / "scripts" / "graph.py"
DOMAIN_DIR = 回放助手.出厂种子  # 包内 assets/破产/：活图由 home 从它拷出，案件那一层的 --domain 也指它
RUNNER = REPO / "scripts" / "skill-eval.py"
EVALS = REPO / "evals" / "用例"
领域名 = "破产"
基线名 = 助手.基线名           # 点开头：用例的「没往工作区乱写」断言按惯例忽略它


def load_runner():
    """借跑器自己的 replay_seed 把「在办中」摊进 案件/：元文件名单只该有一份（scripts/skill-eval.py）。"""
    spec = importlib.util.spec_from_file_location("skill_eval_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


模块 = "接管与调查"
已确认 = "乙公司甲年乙月丙日厂区接管现场情况说明"
已生成 = "乙公司食堂承包合同解除请示"

# 一节点一目录，每版一份文书加一份同名审查报告（ADR-0007）。内容只求形状对，不是真的文书。
DOCS = {
    "文书/%s/%s-v1.md" % (已确认, 已确认):
        "# %s\n\n甲年乙月丙日，管理人到乙公司厂区现场接管，清点厂房一栋、仓库两间，"
        "由丙移交钥匙一串。现场未见第三人占用。\n" % 已确认,
    "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt\n\n"
        "## 存疑点\n\n无\n\n## 待律师裁定\n\n无\n\n## 版式门禁\n\n通过\n\n"
        "## 时限\n\n本节点无明示时限\n" % 已确认,
    "文书/%s/%s-v1.md" % (已生成, 已生成):
        "# %s\n\n乙公司与丙签订的食堂承包合同，管理人拟解除，报请裁定。\n" % 已生成,
    "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt\n\n"
        "## 存疑点\n\n合同原件没在材料里\n\n## 待律师裁定\n\n解除还是继续履行\n\n"
        "## 版式门禁\n\n通过\n\n## 时限\n\n本节点无明示时限\n" % 已生成,
}


def run(cmd, cwd) -> int:
    r = subprocess.run([sys.executable, *[str(c) for c in cmd]], cwd=str(cwd),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    live = 回放助手.用活图(ws, 领域名)   # 没设 LOO0NG_HOME 时它自己落进工作区里的 .活图家/
    case = ws / "案件"
    case.mkdir(parents=True, exist_ok=True)
    load_runner().replay_seed(EVALS, "在办中", case)

    for rel, text in DOCS.items():
        path = case / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # 律师自己长出的两个节点：id 由引擎生成，回流时原样带进活图（ADR-0012）。
    # --domain 仍指包内种子：这一层是案件图的写，领域图只被读来算来源与时限，与「在办中」那一层同一份。
    engine = [ENGINE, "--domain", DOMAIN_DIR]
    steps = [
        [*engine, "add-node", "--module", 模块, "--title", 已确认],
        [*engine, "generate", "--node", 已确认, "--doc", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--source", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认)],
        [*engine, "confirm", "--node", 已确认, "--words", "现场情况说明这份可以了，就这样定"],
        [*engine, "add-node", "--module", 模块, "--title", 已生成],
        [*engine, "generate", "--node", 已生成, "--doc", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--source", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成)],
    ]
    for cmd in steps:
        code = run(cmd, case)
        if code != 0:
            return code

    # 基线让断言不必硬写活图路径与「72 个节点」：下一次入库让出厂种子长大，这份种子跟着长，用例不动。
    domain = json.loads((live / "领域图.json").read_text(encoding="utf-8"))
    基线 = {
        "案件图sha256": hashlib.sha256((case / "图.json").read_bytes()).hexdigest(),
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
