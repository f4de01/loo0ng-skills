# 律师工作台 3.0

破产业务先行的法律工作台，以 skill 形态构建。从零重构，起因与输入见 `docs/3.0-handoff.md`。

## 硬边界（不上桌）

1. **案件材料永不入本仓库**：真实案件材料只存在于仓库外的案件工作区（`D:\Claude\Data\Cases\`）；仓库内所有案件引用只指向外部路径；案件敏感信息不得写入 issue、commit message；机械守门（隐私钩子）见 `docs/adr/0014`。
2. **办案会话对本仓库只读**：在案件目录上工作的会话不写本仓库（含 `knowledge/`）；判为通用的裁定由开发会话誊入，导入的预设图进仓库那次 diff 须经第二双眼；律师一句话另存出的个人预设图写的是 `~/.loo0ng/预设图/` 下那一份，在本仓库之外，不破这条只读（ADR-0023）。

ADR-0001 至 0021 为参考（ADR-0022）：记的是当时为什么这么定，与 skill 正文冲突时以正文为准，引用它们不构成反对一个改动的理由。

## 结构不变量（理由在 ADR-0009）

1. **登记**：每件 skill 同时出现在 `skills/<bucket>/<name>/`（桶照上游五个；办案主线六件在 `engineering/`、`to-docx` 在 `productivity/`）、所在桶的 `README.md`、`.claude-plugin/plugin.json` 的 `skills` 数组、根 `README.md` 两组之一，并有一页 `docs/<bucket>/<name>.md`（后三处只收 promoted 桶 `engineering/`、`productivity/` 里的）；根 README 与桶 README 的条目都把名字链接到它的 `SKILL.md`；`name` 只用小写字母、数字、连字符，不带 `loo0ng-` 前缀（路由照上游 `ask-matt` 形叫 `ask-loo0ng`）；`SKILL.md` 不带 BOM。 详见 [登记与布局](./.agents/registration.md)。
2. **路由两张表同步**：增删或改名任一件 skill，改了律师触发它的那句话，或改了编排 skill 在流程里调谁，必改 `ask-loo0ng` 自持的两张表（打名字的三个入口一张，说一句话就到的四件一张；兄弟地图收在后一张）。 详见 [调用规则](./.agents/invocation.md)。
3. **双旗同步**：编排 skill 与路由同时带 `disable-model-invocation: true` 与 `allow_implicit_invocation: false`；参考 skill 两者都不带。`agents/openai.yaml` 手写，`display_name` 等于 `name`（ADR-0021）。 详见 [调用规则](./.agents/invocation.md)。
4. **relink**：改名、增删 skill 后重跑 `scripts/link-skills.ps1`。 详见 [登记步骤](./.agents/registration.md)。
5. **出厂预设图三样**：`skills/<bucket>/domain/assets/预设图/<名>/` 只有 `预设图.json`、`模板/` 官方模板原件、`指引手册/` 指引手册原文（ADR-0023）；出厂件谁都不许在会话里写，个人预设图在包外的 `~/.loo0ng/预设图/` 下。 详见 [目录布局](./.agents/registration.md)。

6. **机械校验**：改了任何文本文件就跑 `bash scripts/check-text.sh .`（全仓文本规矩：禁破折号 U+2014、非 `.ps1` 不带 BOM、`.ps1` 必须带 BOM）；改了 `skills/`、`docs/`、`README.md` 或 `.claude-plugin/` 另跑 `bash scripts/check-skill.sh .`、`bash scripts/check-wiring.sh .`、`claude plugin validate . --strict`，全绿才提交；改名或删除后另跑 `bash scripts/check-stale.sh . <旧名>`；发版前 `bash scripts/check-release.sh .`（ADR-0021）。 详见 [校验与测试](./.agents/testing.md)。

7. **说明随包自足**：skill 根目录的全部 `*.md` 与 `scripts/` 的说明（含注释、文档字符串、回显）不出现 ADR 号、issue 号、发布版本号，也不指向本 skill 目录之外的仓库文件；运行所需的格式与依赖版本、包内路径、工作区文件名保留，官方模板与指南原件不改（ADR-0025）。 详见 [文档写法](./.agents/writing-docs.md)。

维护时按需读：增删改名与布局见 [登记约定](./.agents/registration.md)；description、双旗与互调见 [调用规则](./.agents/invocation.md)；docs 页与随包说明见 [文档写法](./.agents/writing-docs.md)；验证与触发见 [校验与测试](./.agents/testing.md)；changeset、发布与安装见 [发布与分发](./.agents/release.md)。

开发时按需读：issue 操作见 `docs/agents/issue-tracker.md`（本仓 GitHub Issues，使用 `gh`）；分诊见 `docs/agents/triage-labels.md`（五角色标签）；探索代码与记录领域决策见 `docs/agents/domain.md`（根 `CONTEXT.md` 与 `docs/adr/`）。

## 本文件写什么

本文件每轮整篇进上下文，只装三种东西：硬边界；违反了产品就坏的结构不变量（每条一行，理由在 `docs/adr/`）；指向长约定的一行指针。对模型行为的要求不写在这里：事故的教训在发布时经空话检验后写进它所属 skill 的正文。结构不变量随 `skills/` 目录建立时写入。依据 ADR-0009 与 `docs/research/AGENTS-md-该写什么.md`。
