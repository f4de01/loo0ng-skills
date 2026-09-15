"""种子「重出」：一个已确认的节点又出了一版。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按出厂预设图「破产」起手，再摆出：承诺书已确认、印章备案已确认，之后承诺书又出了一版（法院要求改），
覆盖同一路径、黄色已清，于是它现在是已生成、等律师拍板，旧的确认留在条目里。
仍处于已确认的只剩印章备案。供 skill "ask-loo0ng" 的用例「已确认后重出」。
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
    助手.办完(ws, "管理人印章备案报告", "印章备案这份可以了")
    助手.出一版(ws, "管理人承诺书及团队人员")   # 重出：覆盖同一路径，条目再追加一条
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
