"""种子「模板」：在种子「图引擎」的工作区之上，把一件官方模板放进 参考/模板/，供打清单的用例。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
官方模板原件住出厂预设图 skills/in-progress/domain/assets/预设图/破产/模板/，原位读、拷一件进工作区。
工作区里没有任何案件内容。
"""
import importlib.util
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

GRAPH_SEED_REPLAY = pathlib.Path(__file__).resolve().parent.parent / "图引擎" / "回放.py"
模板名 = "1-2.关于管理人印章备案的报告.docx"


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_graph_replay", GRAPH_SEED_REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code
    源 = 助手.官方模板 / 模板名
    if not 源.is_file():
        sys.stderr.write("找不到官方模板 %s\n" % 源)
        return 1
    shutil.copy2(str(源), str(pathlib.Path(workspace) / "参考" / "模板" / 模板名))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
