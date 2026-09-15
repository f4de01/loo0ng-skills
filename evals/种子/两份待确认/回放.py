"""种子「两份待确认」：两份文书同时等律师拍板，一份黄色已清、一份还没清。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按出厂预设图「破产」起手（12 模块 72 节点整份在图里），再摆出：承诺书已确认；印章备案出了一版、
律师在 Word 里把黄都填掉了（高亮 已清）、还没确认；银行账户备案出了一版、文书里还有黄（未清）、也没确认。
印章备案在图上带时限句、银行账户备案没有；前方第一个是同模块的「管理人工作计划」，它没有时限，
排在它后面的两个倒有：路由若因时限改序就会挑错。
供 skill "ask-loo0ng" 的用例「两份同时待确认」「路由第一行」与 skill "doit" 的用例「跨对话确认」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws, 助手.破产)
    助手.办完(ws, "管理人承诺书及团队人员", "承诺书这份就这样，可以了")
    助手.出一版(ws, "管理人印章备案报告")            # 黄色已清，等一句确认
    助手.出一版(ws, "管理人银行账户备案报告", 高亮=True)   # 还有一处黄
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
