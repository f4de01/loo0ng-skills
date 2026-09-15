"""种子「空图」：刚起手、空图，一个节点都没有的案件工作区。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
空图起手（走真的起手 CLI，不给预设图），此外什么都不做：图里 `模块` 是空数组，前方为空，
参考/模板/ 也空。案件图自足，路由没有别处可看。供 skill "ask-loo0ng" 的用例「空图起手」。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 基线  # noqa: E402
import 回放助手 as 助手  # noqa: E402


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    助手.起手(ws)
    基线.写基线(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
