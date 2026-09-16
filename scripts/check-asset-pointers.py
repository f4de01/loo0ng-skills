"""检查 SKILL.md 的本地参考指针，不把数据位置说明当作阅读指针。"""
import pathlib
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit


def targets(text):
    # Markdown 行内链接（含图片）、引用式链接定义，以及正文中的反引号文件路径。
    patterns = (
        (r'\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)', True),
        (r'^\s*\[[^]\n]+\]:\s*(?:<([^>]+)>|(\S+))', True),
        (r'`([^`\n]+)`', False),
    )
    for pattern, link in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            target = next(group for group in match.groups() if group is not None)
            yield text.count("\n", 0, match.start()) + 1, target, link


def violations(path):
    text = path.read_text(encoding="utf-8")
    # frontmatter 描述的是能力与位置；披露式参考指针在正文中。
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = "\n" * text[:end + 5].count("\n") + text[end + 5:]
    for line, target, link in targets(text):
        target = unquote(target).replace("\\", "/")
        parsed = urlsplit(target)
        windows_drive = re.match(r"^[A-Za-z]:/", target)
        if parsed.scheme and parsed.scheme != "file" and not windows_drive:
            continue
        normalized = posixpath.normpath(parsed.path)
        parts = normalized.split("/")
        if "assets" not in [part.lower() for part in parts]:
            continue
        # 目录位置可写在散文里；链接本身是指针，反引号则须指到文件。
        local = path.parent / normalized
        directory = parsed.path.endswith("/") or local.is_dir()
        if link or (not directory and (pathlib.PurePosixPath(normalized).suffix or local.is_file())):
            yield line, target


if __name__ == "__main__":
    path = pathlib.Path(sys.argv[1])
    hits = list(violations(path))
    for line, target in hits:
        print(f"{path.name}:{line}: 正文指针指向数据目录：{target}")
    sys.exit(bool(hits))
