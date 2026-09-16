# 文档写法

新增或修改 skill 的 docs 页、随包说明时读本篇。目录布局与命名见 [registration.md](./registration.md)，description 与跨 skill 调用句式见 [invocation.md](./invocation.md)。

## docs 页

Promoted 桶（`engineering/`、`productivity/`）每件 skill 有一页 `docs/<bucket>/<name>.md`；`misc/`、`in-progress/`、`deprecated/` 不建这些页。

固定段按以下顺序：

1. What it does
2. When to reach for it
3. Common questions
4. It's working if
5. Where it fits

页内链接一律绝对。根 README 与桶 README 的 skill 名字链接到它的 `SKILL.md`。新增、改名、删除时同步登记，见 [registration.md](./registration.md)。

## 说明随包自足

**说明随包自足（ADR-0025）**：skill 根目录的全部 `*.md` 与 `scripts/` 的说明（含注释、文档字符串、回显）不出现 ADR 号、issue 号、发布版本号，也不指向本 skill 目录之外的仓库文件（`CONTEXT.md`、`AGENTS.md`、`docs/`、`tests/`）。`npx skills add` 与 `claude plugin install` 装过去的只有 `skills/<bucket>/<name>/` 这一个目录，别的都读不到。历史对比句（「以前 X 现在 Y」）与出处标注一并不写；会改变模型判断的内容留下来，改写成判据本身（写「不许 X」，不写「因为当年 Y 所以不许 X」）。`check-skill.sh` 逐件扫根目录 Markdown 与 `scripts/` 文件，白名单放行清单坐标（`p2#1`）、指向本目录兄弟文件的链接、钉住的后端版本号（`python-docx==1.2.0`、`python 3.9.6`）。运行所需的图格式版本、包内路径与工作区文件名仍保留；`assets/` 中的官方模板与指南是原始数据，不按说明清洗。
