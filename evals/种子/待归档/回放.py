"""种子「待归档」：在种子「图引擎」的工作区之上，待归档里放三件各对一个去向的合成文件。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
待归档/ 里的三件由跑器按种子接口原样拷进工作区（起手不挪 待归档/ 自己）；
这里只复用「图引擎」的回放把菜园工作区落下。工作区里没有任何案件内容。
"""
import importlib.util
import pathlib
import sys

GRAPH_SEED_REPLAY = pathlib.Path(__file__).resolve().parent.parent / "图引擎" / "回放.py"
三件 = ("地块记录.txt", "播种日志空表.md", "合作社种植要求.md")


def main(workspace: str) -> int:
    sys.dont_write_bytecode = True  # 别在仓库的种子目录里留 __pycache__
    spec = importlib.util.spec_from_file_location("seed_graph_replay", GRAPH_SEED_REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main(workspace)
    if code != 0:
        return code
    缺 = [名 for 名 in 三件 if not (pathlib.Path(workspace) / "待归档" / 名).is_file()]
    if 缺:
        sys.stderr.write("种子「待归档」要求跑器已把三件拷进 待归档/，缺：%s\n" % "、".join(缺))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
