# 律师工作台 3.0

破产业务先行的法律工作台，以 skill 形态构建。从零重构，起因与输入见 `docs/3.0-handoff.md`。

## 硬边界（不上桌）

1. **案件材料永不入本仓库**：真实案件材料只存在于仓库外的案件工作区（`D:\Claude\Data\Cases\`）；仓库内所有案件引用只指向外部路径；案件敏感信息不得写入 issue、commit message；机械守门（隐私钩子）见 `docs/adr/0014`。
2. **办案会话对本仓库只读**：在案件目录上工作的会话不写本仓库（含 `knowledge/`）；判为通用的裁定由开发会话誊入，导入的预设图进仓库那次 diff 须经第二双眼；律师一句话另存出的个人预设图写的是 `~/.loo0ng/预设图/` 下那一份，在本仓库之外，不破这条只读（ADR-0023）。

ADR-0001 至 0021 为参考（ADR-0022）：记的是当时为什么这么定，与 skill 正文冲突时以正文为准，引用它们不构成反对一个改动的理由。

## 结构不变量（理由在 ADR-0009）

1. **登记**：每件 skill 同时出现在 `skills/<bucket>/<name>/`（桶照上游五个；改造期七件都在 `in-progress/`，毕业后办案主线六件回 `engineering/`、`to-docx` 回 `productivity/`，ADR-0022）、所在桶的 `README.md`、`.claude-plugin/plugin.json` 的 `skills` 数组、根 `README.md` 两组之一，并有一页 `docs/<bucket>/<name>.md`（后三处只收 promoted 桶 `engineering/`、`productivity/` 里的）；根 README 与桶 README 的条目都把名字链接到它的 `SKILL.md`；`name` 只用小写字母、数字、连字符，不带 `loo0ng-` 前缀（路由照上游 `ask-matt` 形叫 `ask-loo0ng`）；`SKILL.md` 不带 BOM。
2. **路由两张表同步**：增删或改名任一件 skill，或改了律师触发它的那句话，必改 `ask-loo0ng` 自持的两张表（打名字的三个入口一张，说一句话就到的四件一张）。
3. **双旗同步**：编排 skill 与路由同时带 `disable-model-invocation: true` 与 `allow_implicit_invocation: false`；参考 skill 两者都不带。`agents/openai.yaml` 手写，`display_name` 等于 `name`（ADR-0021）。
4. **relink**：改名、增删 skill 后重跑 `scripts/link-skills.ps1`。
5. **出厂预设图三样**：`skills/<bucket>/domain/assets/预设图/<名>/` 只有 `预设图.json`、`模板/` 官方模板原件、`指引手册/` 指引手册原文（ADR-0023）；出厂件谁都不许在会话里写，个人预设图在包外的 `~/.loo0ng/预设图/` 下。

6. **机械校验**：改了 `skills/`、`docs/`、`README.md` 或 `.claude-plugin/` 就跑 `bash scripts/check-skill.sh .`、`bash scripts/check-wiring.sh .`、`claude plugin validate . --strict`，全绿才提交；改名或删除后另跑 `bash scripts/check-stale.sh . <旧名>`；发版前 `bash scripts/check-release.sh .`（ADR-0021）。

7. **正文随包自足**：`SKILL.md` 与 `references/*.md` 里不出现 ADR 号、issue 号、版本号，也不指向本 skill 目录之外的仓库文件——装到律师机上的只有这一个目录（ADR-0025）。

长约定见 `docs/agents/skills.md`。

## 本文件写什么

本文件每轮整篇进上下文，只装三种东西：硬边界；违反了产品就坏的结构不变量（每条一行，理由在 `docs/adr/`）；指向长约定的一行指针。对模型行为的要求不写在这里：事故的教训在发布时经空话检验后写进它所属 skill 的正文。结构不变量随 `skills/` 目录建立时写入。依据 ADR-0009 与 `docs/research/AGENTS-md-该写什么.md`。
