"""种子「自加节点」：律师自己加了一个预设图里没有的节点，又把一个节点改了短标题。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
按出厂预设图「破产」起手，再摆出：承诺书出了一版、黄色已清、还没拍板，随后被律师改标题为「承诺书」
（id 不变，起手拷进案件图的那句时限跟着节点走）；模块「接受指定与报备」下、紧跟承诺书之后多一个
预设图里没有的节点「补充材料说明」，未生成，于是它是前方的第一个。
供 skill "ask-loo0ng" 的用例「自加节点与改标题」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws, 助手.破产)
    助手.出一版(ws, "管理人承诺书及团队人员")
    助手.引擎(ws, "add-node", "--module", "接受指定与报备", "--title", "补充材料说明",
            "--after", "管理人承诺书及团队人员")
    助手.引擎(ws, "rename-node", "--node", "管理人承诺书及团队人员", "--title", "承诺书")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
