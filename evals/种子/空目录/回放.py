"""种子「空目录」：还不是案件工作区的目录，只有一个装着待归档合成件的 收件箱/。

用法：python 回放.py <工作区>    （由 scripts/skill-eval.py 调，也可手跑）
收件箱/ 里的文件由跑器按种子接口原样拷进工作区；这里不建任何东西，只守住前置：
起手（setup-case）的前置是当前目录没有 图.json，种子把这条前置摆好就够了。
工作区里没有任何案件内容。
"""
import pathlib
import sys


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    if (ws / "图.json").exists():
        sys.stderr.write("种子「空目录」要求工作区里没有 图.json，实际有\n")
        return 1
    if not (ws / "收件箱").is_dir():
        sys.stderr.write("种子「空目录」要求 收件箱/ 已由跑器拷进工作区，实际没有\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
