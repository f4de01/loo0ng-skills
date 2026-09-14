---
status: accepted
date: 2026-09-05
---

# skill 清单八件，名字带 loo0ng 前缀，仓库照 Matt 平铺，改名即发布，起手把领域目录路径落进工作区

清单票要定哪些成为编排 skill、哪些成为参考 skill、名字怎么起、两平台怎么装、以后怎么改。制图时只说"开发在 Claude Code、律师用 Codex，skill 包两边都要实测"，没有说结构照谁。本票裁定：**skill 设计、仓库结构、维护与分发一律按 Matt Pocock 的 skill 体系**（插件缓存 `mattpocock-skills/1.2.3` 原文与其拆解报告），与之冲突的既有裁定改。

我们决定：

- **清单八件**。编排层两个入口 `loo0ng-setup-case`（起手）、`loo0ng-doit`（办节点，见 ADR-0010），路由 `ask-loo0ng`；参考层四个：`loo0ng-graph`（图的唯一引擎：读写案件图与领域图、条目追加、状态推算、`图视图.md` 覆盖重算、律师一句话改构成）、`loo0ng-domain`（领域目录与雏形机制）、`loo0ng-filing`（收件箱归档搬运与律师陈述落档）、`loo0ng-to-docx`（Markdown→DOCX 冻结转换器、版式门禁两个 CLI、审查报告格式）。图存档与隐私钩子各留一槽，归各自的票。参考层切四份的判据取自 `invocation.md`：「could the model usefully reach for this autonomously?（Reuse is the reason to extract a skill, not the test）」，四个各有律师一句话就该被模型自己够到的场景；`loo0ng-domain` 独立于引擎的依据是 ADR-0004「随 skill 包内置，也可独立交付」。
- **名字**：`name:` 只能小写字母数字连字符（两平台校验硬限），中文只进 `interface.display_name` 与 `metadata.short-description`。前缀 `loo0ng-` 写进 `name:` 本身，路由照 `ask-matt` 形取 `ask-loo0ng`。前缀不靠插件命名空间：那是 Claude Code 装插件时自动加的，Codex 没有对应物。基名照 Matt 的命名族（`setup-…` 一次落盘、`to-X` 把 A 变成 B、动词是动作）。两平台的 `/` 与 `$` 补全都是子串匹配，前缀长短不影响检索。
- **路由是 user-invoked**，与 `ask-matt` 同款（`disable-model-invocation: true` + `allow_implicit_invocation: false`）。
- **description 两套**：user-invoked 一句人话（功能 + 后面跟什么，去掉触发词）；model-invoked 四要素齐全（功能、触发、负向、邻居互指），第三人称、中文、触发词放最前、≤1,024 字。跨 skill 只用「调用 skill "loo0ng-graph"」一种句式，散文用中文显示名；这让改名成为纯机械替换。
- **仓库结构照 Matt 但不分桶**：`skills/<name>/`（`SKILL.md` + 机械生成的 `agents/openai.yaml` + `references/` + `scripts/` + 仅 `loo0ng-domain` 有 `assets/`）。不分桶的依据是 Matt ADR-0002：Codex 插件清单只接受单一路径，分桶让他至今出不了 Codex 插件。草稿放分支不放目录。
- **维护即发布**：改名、改功能都是一次发布，只在开发者维护时做。照抄 changesets + semver + `CHANGELOG.md`、`plugin.json` 版本同步、登记不变量（根 `README.md` 分 User-invoked / Model-invoked 两组 + `plugin.json` 的 `skills` 数组，改完跑 `claude plugin validate . --strict`）、router 同步（增删改名必重读 `ask-loo0ng`）、改后重跑 `scripts/link-skills.ps1`、双旗同步、全仓禁破折号。不照抄 aihero 站点的文档页与分桶。
- **分发照 Matt 双轨**：Claude Code 走插件（`.claude-plugin/plugin.json` + `marketplace.json`，仓库自成单插件市场），Codex 走 skills.sh；`.codex-plugin/plugin.json` 指 `./skills/` 列为实验项。本机开发者即律师，只用 `link-skills.ps1` 条目级 junction 到 `~/.claude/skills/` 与 `~/.agents/skills/`，两条路互斥。上架官方 marketplace、zip、CalVer、别的机器上的实测仍在本图之外。
- **机制 B 落到案件工作区**：Matt 的 setup 往目标仓库写 `docs/agents/*.md` 与 CLAUDE.md 指针块，本项目的"目标仓库"是案件工作区，setup 就是起手。`loo0ng-setup-case` 在工作区根写 `AGENTS.md`（Codex 读）与 `CLAUDE.md`（一行 `@AGENTS.md`；Claude Code 只读 CLAUDE.md）。块里只有：领域名与领域目录绝对路径（机器相关，所以落工作区而不写死在 skill 里）、图与视图文件名、入口名、"本工作区对 skill 仓库只读"。种子模板放在 `loo0ng-setup-case` 文件夹里。硬依赖（`loo0ng-doit`、`ask-loo0ng`、`loo0ng-domain`）正文写一行「领域目录路径应已由工作区提供，没有则让律师跑 loo0ng-setup-case」；软依赖（`loo0ng-graph`、`loo0ng-filing`）只靠 `图.json`，不写。引擎 CLI 的领域目录参数从这里来。这个块不加确认点，由起手图三选一机械推出。
- **领域目录**：`docs/指引手册/` 与 `knowledge/模板/` 搬进 `loo0ng-domain/assets/` 发生在它的实现票；`knowledge/` 其余留作素材。8 个来自既有案件的 `.doc` 不进（硬边界 1）。
- **`AGENTS.md` 照 Matt，不采 legal-skills 的事故驱动写法**。调研 `docs/research/AGENTS-md-该写什么.md` 的结论：这类文件每轮整篇进上下文，只该装三种东西：硬边界、违反了产品就坏的结构不变量（登记、路由同步、双旗同步、relink、领域目录三样）、指向长约定的一行指针（`docs/agents/skills.md`）。对模型行为的要求一律不进 `AGENTS.md`：事故的教训在发布时过 Matt 的空话检验（不写它模型会不会做错）后，写进它所属 skill 的正文，只在那条路上被读到。J11 那种「违反一次、附日期与出处」的规则条不采用。结构不变量随 `skills/` 目录建立时写入，不预建空段。`CLAUDE.md` 改为 `@AGENTS.md` 导入，因为 Claude Code 不自动读 `AGENTS.md`。案件工作区那份 `AGENTS.md` 是起手落下的固定模板，之后没有任何 skill 往里写；案件推进只写 `图.json` 与 `材料/律师陈述/`。
- **完成定义落票**：每张 skill 实现票带固定「完成」段：在 Codex 案件会话里被触发一次（编排 skill 律师打 `$名`，参考 skill 律师一句话由模型够到），Claude Code 同样一次；关票评论只记日期、平台、打的名、结果类别（落盘 / 拒绝 / 生成失败），不引自由文本与工作区路径。开发迭代可在测试工作区做，关票以真实案件为准。

## 考虑过的方案

- 前缀靠插件命名空间：Codex 无此物，skills.sh 拷下去是裸名。
- 拼音基名：长且无 Tab 之外的记忆优势。
- 中文 `name:`：出两平台规范，Codex `$` 提及只认 ASCII；实测票顺手试一次只记结果。
- 归档并进引擎：违反 ADR-0007「两个脚本互不 import」。门禁独立成 skill：没有独立触发场景。
- setup 与起手拆成两个 skill：多出一个入口，与主循环的入口数冲突，律师多记一个名字没换来任何东西。
- 分桶（`in-progress/` 等）：Matt 的教训。
- 把分发整体留在图外：律师机器上装不上就没有"真实案件会话"，完成定义落空。

## 后果

- ADR-0005、ADR-0008 里的 `init` / `draft` / `decide` 字样按本表更名（附注，不重写）；路由原型切到"合并入口"那版、入口表按本表填。
- `CONTEXT.md`：「编排 skill」条入口改两个；新增「领域目录」；「路由」条加"以 ask-loo0ng 之名"不必，名字不进词汇表。
- 新开两票：AFK task「两平台注册、补全与拉取实测」；grilling「测试策略」，被前者阻塞。雾里「规则元规则」由本 ADR 的 `AGENTS.md` 条清掉，「测试策略」毕业为票。ADR-0005 后果里「维护规则的落点等第一次真实违反再写入」改为：路由同步是结构不变量，随 `skills/` 建立时主动写。
- 地图 Notes 加"按 Matt 体系"常设偏好；Out of scope 的分发条改写。

## 附注（2026-09-05，ADR-0011）

「图存档各留一槽」中图存档的槽关闭：图存档是 `loo0ng-graph` 引擎的一个输出（`图视图.json`），不是独立 skill。隐私钩子的槽不变。

## 附注（2026-09-05，ADR-0014）

隐私钩子的槽关闭：它是仓库侧 `scripts/privacy-check.py` + `.githooks/` 两只 shim，只约束开发者，不是 skill，不随 skill 包分发。

## 附注（2026-09-05，ADR-0015）

「开发迭代可在测试工作区做，关票以真实案件为准」展开为 ADR-0015：合入门槛（脚本层测试 + 两侧 eval 全绿）与关票门槛（真实触发一次）是两道门。

## 附注（2026-09-06，#24）

被 #18 推翻或改写的四项按其决议表落进 `docs/agents/skills.md`，本文不重写：(1)「`name:` 只能小写字母数字连字符（两平台校验硬限）」的理由改为 skills.sh 分发链拦非 ASCII 加 Codex `$` 提及只认 ASCII，两平台本身不拦；(2)「改完跑 `claude plugin validate . --strict`」拆为 marketplace 严格、skills 严格、plugin.json 非严格三条；(3)「`.codex-plugin/plugin.json` 指 `./skills/` 列为实验项」升正式；(4)「改后重跑 `link-skills.ps1`」只在改名、增删后。另：「中文只进 `interface.display_name` 与 `metadata.short-description`」里后者是 `SKILL.md` frontmatter 的键（Codex 读），`agents/openai.yaml` 对应的键是 `interface.short_description`，两处都可放中文，本仓库照 Matt 用 openai.yaml 的两个。

## 附注（2026-09-06，#29）

「中文只进 `interface.display_name` 与 `metadata.short-description`」改为只进后者：`display_name` 必须等于 `name`。#29 关票的真实触发里，Codex 的 `$` 补全列表显示的是 `display_name`，律师按 `loo0ng-` 名字找，四条中文显示名一条都对不上；名字本来就是 `name`，显示名不该是第二个名字。短描述那一列仍是中文。生成器 `scripts/gen-openai-yaml.py` 机械校验这一条。

## 附注（2026-09-07，#66）

「开发迭代可在测试工作区做，关票以真实案件为准」的后半句作废，完成定义里「在 Codex 案件会话与 Claude Code 各真实触发一次」中的「案件」随之改口径：**关票触发在从种子生出的临时工作区里做**（`python scripts/skill-eval.py --materialize <种子>` 生一个、两侧各触发一次、用完删），真实案件不再是关票的前提。完成定义的其余部分不变：仍是两侧各一次，关票评论仍只记日期、平台、打的名、结果类别，并写明材料是合成的。

理由：触发要改图，而改图不可逆（节点永不删、不适用是终态，ADR-0003），拿律师在办的案子承担验证性的改图，代价与收益不成比例；#32 起长出来的两个常驻合成目录则两头都不挨着（既非真实案件也非只生不存），每关一票脏一点，撤痕只有标不适用或手改 JSON 两条不受支持的路。做法与适用范围见 ADR-0015 的同日附注。仓库里凡说「真实案件里各触发一次」的地方（本文第 22、51 行，ADR-0006 的验收段，ADR-0015 正文的「真实案件层」与「关票门槛 = 真实触发一次」）一并按这个口径读：「真实」指的是真实的安装与触发路线，不是真实的案件材料；那几处正文照 ADR 惯例不改。

## 附注（2026-09-08，#82）

「清单八件」的那个数作废，实际是**七件**：编排层两个入口加路由，参考层四个，正文第 12 行列的就是这七个。当时另留的两个槽后来各自关掉（图存档由 ADR-0011、隐私钩子由 ADR-0014，见上面两条附注），七加二的加号没了，八这个数也就没了对应物。本文标题与正文照 ADR 惯例不改，凡在别处读到「八件」都按七件读。

活文档三处（`README.md` 的 Skill 清单段、`docs/agents/skills.md` 的目录布局段、`skills/README.md`）随 #82 已改成七件，机械口径以 `skills/` 下的目录数与 `.claude-plugin/plugin.json` 的 `skills` 数组为准，两者都是七条。

## 附注（2026-09-13，分桶）

「仓库结构照 Matt 但不分桶」与「不照抄 aihero 站点的文档页与分桶」两条作废，改为**严格照上游布局**：`skills/` 下五个桶（engineering、productivity、misc、in-progress、deprecated），七件全部住 `productivity/`（上游 CLAUDE.md 对它的定义是「daily non-code workflow tools」，办案正是），另外四桶只有 `README.md`；每桶一份 `README.md` 逐件列出、名字链接到 `SKILL.md`；根 `README.md` 的条目同样链接到 `SKILL.md`（上游明文规则，此前漏了）；promoted 的每件另有一页 `docs/<bucket>/<name>.md`，段序照上游 `.agents/writing-docs.md`。`skills/README.md` 随之删除（上游没有它，桶 README 顶替）。

当初不分桶的依据（Codex 清单只接单一路径）不再成立：`.codex-plugin/plugin.json` 仍指 `./skills/` 递归扫描，五桶里只有 `productivity/` 有 `SKILL.md`，装到的仍是这七件。代价照实写：哪天往 `in-progress/` 或 `misc/` 放了东西，Codex 插件路线会一并装上，那正是上游 ADR-0002 描述的问题，到那时再定。离线兜底包与 `link-skills.ps1` 的链接名仍只取 `<name>`，律师机上 `~/.agents/skills/<name>` 的形状不变。本次不动发布链（`scripts/release.py` 加 `workflow_dispatch` 那套）与路由的覆盖面。

## 附注（2026-09-13，去前缀）

「前缀 `loo0ng-` 写进 `name:` 本身」作废：六件的 `name` 改为裸基名 `setup-case`、`doit`、`graph`、`domain`、`filing`、`to-docx`，路由仍叫 `ask-loo0ng`（照 `ask-matt` 形，本来就不带前缀）。目录名、`display_name`、`plugin.json` 路径、docs 页、测试目录、路由入口表随之同名。当初加前缀的理由是 Codex 没有插件命名空间、怕裸名与别的 skill 撞上；改的理由是律师打的与看到的都是裸名（Codex 路线本来就显示裸名，ADR-0021），前缀只增加要打的字与要记的名，两平台补全都按子串命中，撞名的代价等真撞上再付。无别名，装了旧名的机器要按 README 重装；旧名在 `CHANGELOG.md` 与本文照 ADR 惯例保留。本文标题与正文不改，凡在别处读到 `loo0ng-graph` 这类旧名都按裸基名读。

## 附注（2026-09-13，分桶修正）

上一条附注「七件全部住 `productivity/`」作废。上游的 `engineering/` 装主线（daily code work，`ask-matt`、`tdd`、`implement`、`wayfinder` 都在那里），`productivity/` 装离了主线也能单独用的工具（`grilling`、`handoff`、`writing-for-agents`）；把「非代码」读成字面义才把七件全塞进 `productivity/`，桶就没了信息量。改为：办案主线六件 `ask-loo0ng`、`setup-case`、`doit`、`graph`、`domain`、`filing` 住 `engineering/`（六件都只在有 `图.json` 的工作区里工作），`to-docx` 住 `productivity/`（门禁可对任意 DOCX 跑、转换器默认写临时位置，离了案子也能用）。docs 页随桶：`docs/engineering/<name>.md` 六页、`docs/productivity/to-docx.md` 一页。装到律师机上的形状不变（链接名与 skills.sh 的目录名都只取 `<name>`）。

## 附注（2026-09-14，开发机两条路各 harness 择一）

「本机开发者即律师，只用 `link-skills.ps1` 条目级 junction 到两个目录」改为照上游 install-block「两条路互斥」按 harness 择一：Claude Code 侧装插件 `loo0ng-skills@loo0ng-marketplace`，Codex 侧挂 junction。起因是去前缀（同日前一条附注）之后裸名在 Claude Code 的 `/` 列表里与本机四十多件别的 skill 混在一起、tab 补不出来；插件的 `loo0ng-skills:` 命名空间顶替了原来写进 name 的前缀，这正是本文当年「前缀不靠插件命名空间」那条反过来的用法，Codex 没有命名空间的问题由 `$` 补全按子串命中兜住。代价：Claude Code 侧看到的是 `claude plugin update` 拉到的 GitHub 默认分支那一版，不是工作副本；测未合并的分支要先把市场换成本仓库绝对路径（`docs/agents/skills.md`「分发事实」）。跑器 `skill-eval.py` 的 Claude Code 侧随之拼 `/loo0ng-skills:<skill>`，`--claude-plugin ""` 退回裸名。
