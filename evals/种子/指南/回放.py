"""种子「指南」：在种子「图引擎」的工作区之上，参考/指南/ 里归进一份案件级指南，供雏形用例。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
指南由跑器按种子接口拷进工作区的 待归档/，这里复用「图引擎」的回放把菜园工作区落下，
再经归档 CLI 把它搬进 参考/指南/（归档索引也就有了它那一行）。工作区里没有任何案件内容。
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

GRAPH_SEED_REPLAY = pathlib.Path(__file__).resolve().parent.parent / "图引擎" / "回放.py"
指南 = "种植指南.md"


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_graph_replay", GRAPH_SEED_REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code
    助手.归档(workspace, [{"路径": 指南, "去向": "参考/指南", "说明": "地块管理处对承包户的统一要求，按环节分列"}])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
