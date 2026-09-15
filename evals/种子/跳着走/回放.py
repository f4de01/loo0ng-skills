"""种子「跳着走」：律师跳过前面几块，先办了后面一块里的一个节点。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按出厂预设图「破产」起手，再摆出：模块「接受指定与报备」的承诺书已确认，
模块「债权通知与审查」的债权表也已确认（确认最晚）。案件图自足：前方按图序从第一个模块算起，
第一个没生成的是「管理人工作计划」，路由不因律师跳着走就改序（ADR-0023）。
供 skill "ask-loo0ng" 的用例「跳着走」。
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
    助手.办完(ws, "债权表", "债权表这份可以了")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
