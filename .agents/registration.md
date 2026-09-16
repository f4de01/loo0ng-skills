# Skill 登记与目录布局

新增、改名、删除 skill 或调整包内布局时读本篇。调用与双旗见 [invocation.md](./invocation.md)，文档页见 [writing-docs.md](./writing-docs.md)，校验见 [testing.md](./testing.md)，发布与分发见 [release.md](./release.md)。文中代码路径均相对仓库根目录，命令在仓库根目录执行。仓库结构与分发照 Matt Pocock 的 skill 体系（ADR-0009），被实测推翻的四项按 #18 的决议表。

## 目录布局

```
skills/<bucket>/<name>/       # 桶照上游五个：engineering、productivity、misc、in-progress、deprecated；办案主线六件在 engineering/，to-docx 在 productivity/，另外三桶只有 README
├── SKILL.md              # frontmatter：name、description；编排 skill 与路由另加 disable-model-invocation: true
├── agents/openai.yaml    # Codex 侧外观：interface.display_name（= name）、interface.short_description（中文进这里）；编排 skill 与路由另加 policy.allow_implicit_invocation: false
├── *.md                  # 披露式参考文件与 SKILL.md 同级，指针用 ./文件名.md
├── requirements.txt      # 只有 to-docx 有：填模板脚本后端的精确钉（python-docx==1.2.0，ADR-0018）。随包到律师机，agent 自备环境时按它装；仓库根上放到不了那里
├── scripts/              # 标准库零依赖的 CLI；只有 to-docx 的 fill.py 例外（python-docx，ADR-0023）。互不 import；跨 skill 一律以子进程互调、默认按兄弟目录找：要写图的（domain 的雏形与另存、setup-case 的起手与既有成品登记）调 graph 的引擎，起手列预设图与按名解析路径调 domain 的 preset.py（ADR-0023）
└── assets/               # 由代码读取或拷贝的数据载荷，允许嵌套，所有 skill 均可使用
```

根目录放 `SKILL.md`、兄弟 prose 文件与单文件模板。子目录按角色只收三类：`agents/` 放 `openai.yaml`，`scripts/` 放可执行脚本，`assets/` 放由代码读取或拷贝的数据；只有 `assets/` 允许嵌套，其余目录只有一层。判据是由谁读取，不是后缀：数据里的 Markdown 指引手册仍是数据。`SKILL.md` 正文的披露式参考指针只能指向同级兄弟文件，不能指向 `assets/` 下任何文件；数据按名经代码解析，目录位置说明不是阅读指针。`check-skill.sh` 检查角色、深度与数据指针，指针包括 Markdown 链接、引用式链接和反引号文件路径。检查需要 Python（默认 `python3`，找不到则 `python`，可用 `PYTHON` 指定解释器）。跑测试时设 `PYTHONDONTWRITEBYTECODE=1`，避免生成不属于分发布局的缓存目录。

`assets/` 用来容纳多文件嵌套载荷：上游 `mattpocock/skills@959a8e9` 的单文件模板直接放根目录，没有多文件载荷树的先例；目录在这里按数据角色引入，不绑定某件 skill。当前 `domain` 的出厂预设图位于 `assets/预设图/<名>/`，包含 `预设图.json`、`模板/` 官方原件与 `指引手册/` 原文，随包整体替换、原位读取（ADR-0023）；产品约束不变。

分桶照上游（ADR-0009 的 2026-09-13 附注）：`skills/` 下五个桶，每桶一份 `README.md` 逐件列出、名字链接到 `./<name>/SKILL.md`；promoted 桶（`engineering/`、`productivity/`）里的每件进 `.claude-plugin/plugin.json` 与根 `README.md`（名字链接到 `SKILL.md`），并有一页 `docs/<bucket>/<name>.md`（写法见 [文档页约定](./writing-docs.md)）；`misc/`、`in-progress/`、`deprecated/` 里的不进这三处。上游 `engineering/` 装的是主线（daily code work），`productivity/` 装的是离了主线也能单独用的工具；对应到这里，办案主线六件（`ask-loo0ng`、`setup-case`、`doit`、`graph`、`domain`、`filing`，都只在有 `图.json` 的工作区里工作）在 `engineering/`，`to-docx`（清单可对任意 DOCX 打、施加默认写临时位置）在 `productivity/`；另外三桶目前只有 README。草稿放分支不放目录，要公开试用的才进 `in-progress/`。分发清单只有一份：`.claude-plugin/plugin.json` 的 `skills` 数组逐件列路径（Claude Code 插件）；`.claude-plugin/marketplace.json` 让仓库自成单插件市场。不发 Codex 原生插件，Codex 及其他 harness 经 skills.sh 装编辑副本（ADR-0021，与上游 ADR-0002 同一个理由：Codex 清单只收单一路径，分桶后会把 `in-progress/` 一并装出去）。

## 命名与编码

- 披露式参考文件与 `SKILL.md` 同级，正文用 `[文件名](./文件名.md)` 指向它。格式与规格类用大写连字符名（如 `GRAPH-FORMAT.md`），分支与说明类用小写连字符名（如 `time-limits.md`）。这是 #53 的裁定：按 `mattpocock/skills@959a8e9` 的兄弟文件形态摊平，参考内容仍按需读取。

- `name` 只用小写字母、数字、连字符，基名裸着写、不带 `loo0ng-` 前缀（ADR-0009 的 2026-09-13 附注「去前缀」）；路由照上游 `ask-matt` 形叫 `ask-loo0ng`。ASCII 的理由：skills.sh 分发链把非 ASCII 名装成 `unnamed-skill`，Codex `$` 提及只认 ASCII；两平台本身不拦（#18 项 1）。目录名与 `name` 一致。
- `agents/openai.yaml` 手写，照上游（ADR-0021）：`interface.display_name` 等于 `name`（Codex 的 `$` 补全列表显示的是它，律师按 `name` 那个名字找，中文显示名反而找不到，#29），`interface.short_description` 写中文短描述。frontmatter 只用上游那四个键（`name`、`description`、`disable-model-invocation`、`argument-hint`），不再有 `metadata` 块。
- `SKILL.md`、`agents/openai.yaml` 与所有 PowerShell 以外的文本文件不带 BOM：带 BOM 的 `SKILL.md` 会让 Codex 静默跳过整个根目录（#20）。PowerShell 5.1 脚本必须带 UTF-8 BOM，否则中文注释按 ANSI 读会撕坏语法（#18）。
- 随包分发的脚本（`skills/*/*/scripts/*.py`）与种子回放（`evals/种子/*/回放.py`）跑得动 python 3.9：律师那台 mac 的 `/usr/bin/python3` 是 3.9.6，图引擎一处 3.10 的 `Path.write_text(newline=)` 就让每一次写图全炸（#61）。`tests/python-floor/` 机械守着这条：按 3.9 的 feature_version 解析，外加认得出形状的 3.10 API。`scripts/` 与 `tests/` 下的开发侧脚本不受这条约束（ADR-0015：它们只在开发机上跑）。
- 全仓禁破折号（U+2014）。连接号 U+2013 用于数字区间，不在此列。
- frontmatter 的 `description` 加双引号：不加引号时 ` #` 起 YAML 注释，两平台都把其后的字截掉（#24 空壳验证时发现）。

## 登记步骤（新增、改名、删除都走一遍）

1. `skills/<bucket>/<name>/` 落目录（主线进 `engineering/`，离了案子也能用的进 `productivity/`），按上面的布局与命名、编码规则；所在桶的 `README.md` 加（或改、删）一行，名字链接到 `./<name>/SKILL.md`。
2. 双旗按 [调用规则](./invocation.md) 的类型写齐：`SKILL.md` 里写旗，手写 `agents/openai.yaml`（`display_name` 等于 `name`）。
3. `.claude-plugin/plugin.json` 的 `skills` 数组加（或改、删）`./skills/<bucket>/<name>`。
4. `README.md` 的 User-invoked 或 Model-invoked 组加（或改、删）一行，名字链接到 `./skills/<bucket>/<name>/SKILL.md`；再建（或改名、删）`docs/<bucket>/<name>.md`。
5. 动到七件里的任一件（名字、律师触发它的那句话、职责）时，改 `ask-loo0ng` 自持的两张表：打名字的三个入口（`setup-case`、`doit`、`ask-loo0ng`）一张，说一句话就到的四件（`filing`、`graph`、`domain`、`to-docx`）一张（ADR-0005、ADR-0023）。
6. 重跑 relink：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1`（只对靠 junction 的那一侧有意义；Claude Code 侧装了插件时脚本自动跳过那个目录，Codex 侧走 skills.sh 时不跑）。改内容不用重跑，只有改名、增删要。Claude Code 侧要看到改动得 `claude plugin update loo0ng-skills@loo0ng-marketplace`，它只取 GitHub 默认分支；要测未合并的分支，先按 [发布与分发](./release.md) 的「分发事实」把市场换成本仓库绝对路径。
7. `npm run changeset` 写一条 changeset。
8. 跑 [校验与测试](./testing.md)。
