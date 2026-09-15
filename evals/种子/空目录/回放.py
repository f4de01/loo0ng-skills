"""种子「空目录」：还不是案件工作区的目录，律师随手丢了六件合成文件在根上；家里另有一份个人预设图。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
根上的六件由跑器按种子接口原样拷进工作区；起手（skill "setup-case"）会把它们挪进 待归档/。
这里只做两件事：守住前置（没有 图.json），并在家里造一份个人预设图「菜园」，让起手那一问
的列表分出厂、个人两组各有一份（供用例「起手一问二选」）。家取环境变量 LOO0NG_HOME，
没设就落在工作区里的 .预设图家/（点开头，起手不挪它）。工作区里没有任何案件内容。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "共用"))
import 回放助手 as 助手  # noqa: E402

根上的六件 = ("债务人移交物品清单.txt", "甲法院破产案件管理人工作提示.md", "（格式）债权申报登记表.md",
           "本所自用-接管物品交接单空表.md", "未命名.txt", "管理人承诺书（已交法院）.md")


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    if (ws / "图.json").exists():
        sys.stderr.write("种子「空目录」要求工作区里没有 图.json，实际有\n")
        return 1
    缺 = [名 for 名 in 根上的六件 if not (ws / 名).is_file()]
    if 缺:
        sys.stderr.write("种子「空目录」要求跑器已把根上那六件拷进工作区，缺：%s\n" % "、".join(缺))
        return 1
    助手.造菜园(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
