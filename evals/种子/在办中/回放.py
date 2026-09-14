"""种子「在办中」：一个已经办了几步的测试工作区。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按真实的破产领域目录整份起手（走真的起手 CLI，六格、工作区指针块与图上挂到的官方模板原件都由它落），
再逐条调图引擎与陈述落档建状态：节点「管理人承诺书及团队人员」已确认、节点「管理人印章备案报告」
已生成未确认、两条律师陈述。
材料/债务人移交物品清单.txt 由跑器按种子接口原样拷进工作区（两份审查报告写着以它为依据）。
工作区里没有任何案件内容：文书与审查报告都是合成的几行字，当事人与法院一律写甲乙丙。
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
SETUP = REPO / "skills" / "productivity" / "loo0ng-setup-case" / "scripts" / "setup.py"
ENGINE = REPO / "skills" / "productivity" / "loo0ng-graph" / "scripts" / "graph.py"
STATEMENT = REPO / "skills" / "productivity" / "loo0ng-filing" / "scripts" / "statement.py"
DOMAIN_DIR = REPO / "skills" / "productivity" / "loo0ng-domain" / "assets" / "破产"

已确认 = "管理人承诺书及团队人员"
已生成 = "管理人印章备案报告"

# 一节点一目录，每版一份文书加一份同名审查报告（ADR-0007）。内容只求形状对，不是真的文书。
DOCS = {
    "文书/%s/%s-v1.md" % (已确认, 已确认): "# %s\n\n本所接受贵院指定担任乙公司破产清算案管理人，承诺勤勉尽责。\n"
                                           "团队：甲（负责人）、乙（债权审查）、丙（财产接管）。\n" % 已确认,
    "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt\n\n"
        "## 存疑点\n\n无\n\n## 待律师裁定\n\n无\n\n## 版式门禁\n\n通过\n\n"
        "## 时限\n\n规则：自收到指定管理人决定书之日起 3 日内组建工作团队进驻债务人企业，"
        "并将团队情况向法院报备（手册，法院要求）\n基准日：甲年乙月丙日，"
        "[律师陈述·直接陈述] 材料/律师陈述/<收到决定书那条>：收到日 甲年乙月丙日\n"
        "推算截止日：甲年乙月丁日（不顺延节假日）\n" % 已确认,
    "文书/%s/%s-v1.md" % (已生成, 已生成): "# %s\n\n管理人已刻制乙公司管理人章一枚，现将印章备案。\n" % 已生成,
    "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成):
        "# %s 第 1 版审查报告\n\n## 生成依据\n\n材料/债务人移交物品清单.txt；"
        "空白模板 官方 1-2.关于管理人印章备案的报告.docx\n\n"
        "## 存疑点\n\n无\n\n## 待律师裁定\n\n启用时间材料里没有\n\n## 版式门禁\n\n通过\n\n"
        "## 时限\n\n规则：自收到《刻制管理人公章函》之日起 3 日内刻制管理人公章，"
        "交法院封样备案后启用（手册，法院要求）\n基准日：缺失\n推算截止日：基准日缺失，算不出\n" % 已生成,
}


def run(cmd, ws):
    r = subprocess.run([sys.executable, *cmd], cwd=str(ws), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + "\n")
    return r.returncode


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    code = run([str(SETUP), "init", "--full", "--domain", str(DOMAIN_DIR), "--workspace", str(ws)], ws)
    if code != 0:
        return code

    for rel, text in DOCS.items():
        path = ws / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # 引擎每次写图都重算两份视图，来源与时限按 id 从领域图查出，所以每条都带 --domain。
    engine = [str(ENGINE), "--domain", str(DOMAIN_DIR)]
    steps = [
        # 一版已生成，律师一句话确认，状态 已确认。
        [*engine, "generate", "--node", 已确认, "--doc", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--source", "文书/%s/%s-v1.md" % (已确认, 已确认),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已确认, 已确认)],
        [*engine, "confirm", "--node", 已确认, "--words", "承诺书这份就这样，可以了"],
        # 一版已生成，还没拍板，状态 已生成。
        [*engine, "generate", "--node", 已生成, "--doc", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--source", "文书/%s/%s-v1.md" % (已生成, 已生成),
         "--review", "文书/%s/%s-v1-审查报告.md" % (已生成, 已生成)],
        # 两条律师陈述：一条直接陈述、一条裁定。
        [str(STATEMENT), "--nature", "直接陈述", "--title", "收到指定决定书的日期",
         "--words", "指定管理人决定书是甲年乙月丙日收到的。", "--node", 已确认],
        [str(STATEMENT), "--nature", "裁定", "--title", "先办印章再办账户",
         "--question", "印章备案与账户备案先办哪一个", "--words", "先把印章备案办完再动账户。"],
    ]
    for cmd in steps:
        code = run(cmd, ws)
        if code != 0:
            return code
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
