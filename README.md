# 律师工作台 3.0

给破产管理人律师用的法律工作台，以 skill 形态交付，装进 Claude Code 或 Codex 就能用。

一个案子在一台机器上的一个目录里长出来：材料、指南、模板、出好的文书都在这个目录里，工作台另用一张**图**记着这个案子有哪些节点、各自走到了哪一步。律师不背流程、不填表格，一句自由文本说要办哪件事就行。

## 装了能干什么

三件事，三句话。下面写的是律师实际打出去的那一串：Claude Code 里 `/名 …`，Codex 里 `$名 …`；装法不同，名字前面可能多一段 `loo0ng-skills:`，见下面的安装段。

**起手一个案子**：在一个空目录里打 `/loo0ng-setup-case`，一案一次。它把案件工作区的目录建起来，这个案子的图三选一（空图、整份「破产」领域图的 12 模块 72 节点、或开发者交付的定制图）；你起手前放好的本案指引它整读一遍，末尾给你一张清单，你说一句话拍板才作数。

**出一版文书**：新到的材料丢进 `收件箱/`，打 `/loo0ng-doit 出一版 裁定确认无异议债权的申请`。一个对话办一份文书：它先把收件箱里的东西各归各位，再读这个案子的材料、指南、空白模板与你过往的文书，照该节点的官方模板出一份 DOCX，附一份审查报告（写明生成依据、存疑之处、要你裁定的地方），出件前过一道版式门禁。你看完说一句「确认」，这一份就完成了。反过来也行：文书你自己写好了，交给它登记并检查一遍。

**问接下来做什么**：`/ask-loo0ng`。一张只读的地图，随时可以问，也可以一直不问。它答你现在在哪、上一件完成的是什么、下一件该办哪个，给出往下的路与每一步的拍板点，最后把你下一句该打的那一串整个写出来。它自己不动任何东西。

你的案件材料只在你自己的机器上：工作台读写的是案件工作区那个目录，本仓库不收任何案件材料。

## 安装

两条路二选一：插件是只读的整包订阅，skills.sh 把 skill 文件拷进你的项目由你改。两条都装，每件 skill 会出现两次。

<details>
<summary><strong>Claude Code：插件</strong></summary>

本仓库自成单插件市场（`.claude-plugin/marketplace.json`），在会话里：

```
/plugin marketplace add f4de01/loo0ng-skills
/plugin install loo0ng-skills@loo0ng-marketplace
```

`owner/repo` 形式只取默认分支；要装某个分支，用 `https://github.com/f4de01/loo0ng-skills.git#<branch>`。**安装源须是公开仓库**：「私有仓库凭本机 gh 或 git 凭据克隆」只在开发机上验过，律师那台 mac 上私有仓库一条都没走通，本仓库为此转成了 public（`docs/实测/mac-20260909/结论.md`）。装上后 skill 名带 `loo0ng-skills:` 前缀，例如 `/loo0ng-skills:ask-loo0ng`。

</details>

<details>
<summary><strong>Codex 及其他 agent：skills.sh</strong></summary>

```bash
npx skills@latest add f4de01/loo0ng-skills -a codex -a claude-code
```

**安装源同样须是公开仓库**：律师那台 mac 上这一条对私有仓库失败过三次，转 public 之后才装上（`docs/实测/mac-20260909/结论.md`）。安装器让你挑 skill 与目标 agent；`-a` 可重复，一次装到两个 harness。

</details>

<details>
<summary><strong>开发者本机：junction</strong></summary>

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1
```

把 `skills/<name>/` 逐条以 junction 挂到 `~/.claude/skills/` 与 `~/.agents/skills/`，顺手设 `core.hooksPath` 启用隐私钩子。改 skill 内容即时生效；只在改名、增删 skill 后重跑。与插件同装时 Codex 会列出同名两条。

</details>

## Skill 清单

按谁能触发分两组。七件的名单与分工见 ADR-0009；两组随实现票逐件填入。仓库布局照上游分桶，七件都住 `skills/productivity/`（各桶的清单在 `skills/<bucket>/README.md`）；每件另有一页面向人的说明：`docs/productivity/<name>.md`。

**User-invoked**

律师打名字触发：Claude Code 里是 `/名 …`，Codex 里是 `$名 …`。这一组只做编排，模型不会自己调用它们。

- **[loo0ng-setup-case](./skills/productivity/loo0ng-setup-case/SKILL.md)**（起手）：在一个空目录里长出案件工作区，一案一次。一条命令落下六格（`收件箱/`、`材料/律师陈述/`、`指南/`、`模板/官方/`、`模板/生成/`、`文书/`）、起手图三选一（空图、整份领域图、开发者交付的定制图）、起手图挂到的官方模板原件与工作区指针块（`AGENTS.md` 记领域目录绝对路径、图与视图文件名、入口名与只读声明，`CLAUDE.md` 一行引它）；再归档收件箱、`指南/` 非空则跑一次雏形，末尾把雏形与既有成品的建议登记合成一张起手清单，律师一句话拍板后才写图。既有成品登记为已生成、来源律师，确认永不自动。
- **[loo0ng-doit](./skills/productivity/loo0ng-doit/SKILL.md)**（办节点）：一个对话办一个节点。律师一句自由文本说动作加节点：「出一版 X」走归档、复制律师指的文件、惰性建节点、整读材料指南模板与过往文书、写 Markdown 最小集、转换、门禁、落盘 `文书/<节点标题>/` 三件、经图引擎追加生成条目、回显审查报告要点；「X 我自己写好了」跑一次只披露不阻断的门禁后登记为已生成、来源律师；「确认 X」「X 不适用」「模块 Y 不适用」经引擎落一条原样存着律师那句话的条目，确认之后若领域图里没有这个节点，再问一次它该归哪儿（模块默认继承案件图里那个、标题去案件化、不问时限），律师一句话之后才经引擎写进本机活图，未拍板不写（ADR-0019）。生成不问缺事实，缺项进审查报告的待律师裁定，律师答一句先落成陈述再重出。拍板也在这个对话里说，下一个节点开新对话。
- **[ask-loo0ng](./skills/productivity/ask-loo0ng/SKILL.md)**（问路）：随时可问的只读地图，可选，永远不是流程里的一步。读 `图.json` 与按顶层「领域」名找到的领域图（靠 id 对应），答当前节点（已生成待确认，可复数）、上一完成（仍处于已确认里确认最晚的）、下一任务（先列全部待确认，再由五问有序决策树定一个，回复里标出命中哪一问）；再给往下的路（每步标出拍板点、要不要开新对话，带时限的节点原样附上那句话）、相近入口的分界线，最后给下一句该打的整串（`/名 …` 或 `$名 …`，裸名），然后停。它自持入口表不读目录，不触发 skill、不写图、不替律师按下去；说的事在图里对不上就说对不上并指向 `loo0ng-doit`，不编入口。

**Model-invoked**

参考 skill 由模型够到，律师无需记名：律师一句话说到相关的事，模型自行调用。

- **[loo0ng-graph](./skills/productivity/loo0ng-graph/SKILL.md)**（图引擎）：`图.json` 的唯一写入口。律师一句话改图的构成（加节点、改标题、调顺序、跨模块移动、改空白模板、增删改模块、节点或模块不适用）由它落盘并回显；编排 skill 经它追加生成与确认条目；每次写图后重算 `图视图.md` 与 `图视图.json`。
- **[loo0ng-domain](./skills/productivity/loo0ng-domain/SKILL.md)**（领域目录与雏形）：领域目录三样的家（领域图、官方模板原件、指引手册原文；内置「破产」，领域图 12 模块 72 节点，由两份通用指引手册跑雏形长出）与雏形机制的零依赖 CLI。领域目录分两份（ADR-0019）：`assets/<领域>/` 是随包分发的出厂种子，`~/.loo0ng/领域/<领域>/` 是律师那台机上的活图，`home` 在首次起手时从种子拷出、已有就一个字不动，skill 包升级碰不到活图。模型整读指南或指引手册写成雏形文件，`check` 按标题判重（同名不重复提出、相似不同名列为待定）并回显清单、图一字不动，律师一句话拍板后 `apply` 逐条经图引擎写入；回流有两条路（ADR-0019）：律师侧逐节点在确认那一刻写活图、没有第二双眼，开发侧批量用 `from-case` 从案件图算候选、保留原 id，写的也是活图（ADR-0020：领域图的构建两侧同一条路，包内出厂种子谁都不许在会话里写，改由入库更新、由第二双眼守）；`docx-text` 把 docx 打成纯文本供整读。它不含领域语义，没有领域图也能从空图起手。
- **[loo0ng-filing](./skills/productivity/loo0ng-filing/SKILL.md)**（归档与陈述）：两个零依赖 CLI，互不引用。归档搬运把收件箱里的文件按相对路径原样搬到材料、指南、模板/官方、模板/生成（判断去向归模型，不改名、不覆盖、不越界）；陈述落档把律师在对话里说的一句话落成 `材料/律师陈述/` 下一条一文件、落盘后只读（六字段头部、原话逐字、整条取代）。起手末尾、出一版开场与律师一句话三处进入。
- **[loo0ng-to-docx](./skills/productivity/loo0ng-to-docx/SKILL.md)**（出件与门禁）：两个 CLI，互不引用。转换器把模型写的 Markdown 最小集以该节点的官方模板为版式载体转成 DOCX（段落格式与字体照模板，表格的列宽、行高、格式照抄，合并单元格用 `<` `^` 约定），只依赖 python-docx、离线，默认写到临时位置；门禁对任意 DOCX 做只读检查，本体零第三方依赖（静态检查加 CJK 版面推算），有 Word COM 时以真实渲染取代推算的区间；结论三档（通过 / 需人眼 / 不通过），通过与需人眼 `--deliver` 一次性落进 `文书/`，不通过不落盘。缺渲染器不阻断出件，测不准也不算通过（ADR-0017）。审查报告格式、最小集与合并约定在它的 `references/`。

## 给开发者

七件 skill 在 Claude Code 与 Codex 两个 harness 上都能触发。

硬边界两条写在 `AGENTS.md`：案件材料永不进本仓库，办案会话对本仓库只读。词汇以 `CONTEXT.md` 为准，决策记在 `docs/adr/`，结构不变量与长约定在 `AGENTS.md` 与 `docs/agents/`。

### 维护

登记步骤、校验命令与测试命令见 `docs/agents/skills.md`。发布链照上游 mattpocock/skills：每次修改写一张 changeset，推到 `main` 后 `.github/workflows/release.yml` 里的 changesets/action 自动开一个 "chore: version skills" 的 PR，合并即打 tag；`package.json` 的版本由 `scripts/sync-plugin-version.mjs` 抄进 `.claude-plugin/plugin.json`，版本记录在 `CHANGELOG.md`。测试、eval 与版式门禁仍然全部本地跑（ADR-0015 2026-09-12 附注）。

发完一版要装到律师那台机器上时，照 `docs/交付/现场清单.md` 现场做，结果填 `docs/交付/记录表.md`：那是开发者本人在那台机器前的四段（装、跑得动转换器的环境、起手一个案子、跑通一个节点），断网可用。

## 许可

代码与文档按 [MIT](LICENSE) 授权。`skills/productivity/loo0ng-domain/assets/<领域>/` 下的官方模板原件与指引手册原文是第三方文件，不在 MIT 的覆盖范围内，各依其自身来源的条款：范围说明在 `LICENSE` 末尾。
