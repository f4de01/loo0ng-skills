"""种子「图引擎」：用合成小领域「菜园」（一份个人预设图）整份起手一个测试工作区。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
先在家里用引擎造出个人预设图「菜园」（4 模块 9 节点，两个挂空白模板、两个带时限），再走真的起手 CLI
`init --preset 菜园 --owner 个人`：目录形状、图与两份视图、两件空白模板、指针块都由它落。
家取环境变量 LOO0NG_HOME，没设就落在工作区里的 .预设图家/。工作区里没有任何案件内容，也没有破产语义。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.造菜园(ws)
    助手.起手(ws, 助手.菜园, "个人")
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
